import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None

    class FileSystemEventHandler:
        pass

from src.database import upsert_file, log_access_event
from src.logger import get_logger

logger = get_logger("watcher")

IGNORED_EXTENSIONS = {".pyc", ".swp", ".tmp", ".lock", ""}
IGNORED_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".intentstore"}


def should_ignore(path):
    try:
        parts = path.split(os.sep)
        for part in parts:
            if part in IGNORED_DIRS:
                return True
        ext = os.path.splitext(path)[1].lower()
        if ext in IGNORED_EXTENSIONS:
            return True
        return False
    except (AttributeError, TypeError):
        return True


class IntentStoreHandler(FileSystemEventHandler):
    def __init__(self, on_new_file=None):
        super().__init__()
        self.on_new_file = on_new_file

    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if should_ignore(path):
            return
        self._register_file(path, "CREATE")

    def on_modified(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if should_ignore(path):
            return
        try:
            log_access_event(path, "MODIFY")
        except Exception as exc:
            logger.error("Failed to log modify event for %s: %s", path, exc)

    def on_deleted(self, event):
        if event.is_directory:
            return
        try:
            log_access_event(event.src_path, "DELETE")
        except Exception as exc:
            logger.error("Failed to log delete event for %s: %s", event.src_path, exc)

    def _register_file(self, path, event_type):
        try:
            stat = os.stat(path)
            size = stat.st_size
            ext = os.path.splitext(path)[1].lower()
            mtime = stat.st_mtime
            upsert_file(path, size, ext, mtime)
            log_access_event(path, event_type)
            logger.info("%s: %s", event_type, path)
            if self.on_new_file:
                self.on_new_file(path)
        except FileNotFoundError:
            logger.debug("File vanished before registration: %s", path)
        except OSError as exc:
            logger.warning("Could not register %s: %s", path, exc)


def scan_directory(directory, on_new_file=None):
    if not os.path.isdir(directory):
        logger.error("Not a directory: %s", directory)
        return 0

    logger.info("Scanning: %s", directory)
    count = 0
    try:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for fname in files:
                fpath = os.path.join(root, fname)
                if should_ignore(fpath):
                    continue
                try:
                    stat = os.stat(fpath)
                    ext = os.path.splitext(fpath)[1].lower()
                    upsert_file(fpath, stat.st_size, ext, stat.st_mtime)
                    count += 1
                    if on_new_file:
                        on_new_file(fpath)
                except (PermissionError, FileNotFoundError) as exc:
                    logger.debug("Skipped %s: %s", fpath, exc)
                except OSError as exc:
                    logger.warning("Error scanning %s: %s", fpath, exc)
    except OSError as exc:
        logger.error("Directory walk failed for %s: %s", directory, exc)

    logger.info("Found %d files in %s", count, directory)
    return count


def start_watcher(directories, on_new_file=None):
    if not WATCHDOG_AVAILABLE:
        logger.error("watchdog package not installed — live watch unavailable")
        return None

    try:
        handler = IntentStoreHandler(on_new_file=on_new_file)
        observer = Observer()
        for d in directories:
            if os.path.isdir(d):
                observer.schedule(handler, d, recursive=True)
                logger.info("Watching: %s", d)
        observer.start()
        return observer
    except Exception as exc:
        logger.error("Failed to start watcher: %s", exc)
        return None


def stop_watcher(observer):
    if observer is None:
        return
    try:
        observer.stop()
        observer.join()
        logger.info("Watcher stopped")
    except Exception as exc:
        logger.error("Error stopping watcher: %s", exc)
