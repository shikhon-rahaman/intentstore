import os
import time
import sys
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from src.database import upsert_file, log_access_event

IGNORED_EXTENSIONS = {".pyc", ".swp", ".tmp", ".lock", ""}
IGNORED_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".intentstore"}


def should_ignore(path):
    parts = path.split(os.sep)
    for part in parts:
        if part in IGNORED_DIRS:
            return True
    ext = os.path.splitext(path)[1].lower()
    if ext in IGNORED_EXTENSIONS:
        return True
    return False


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
        log_access_event(path, "MODIFY")

    def on_deleted(self, event):
        if event.is_directory:
            return
        log_access_event(event.src_path, "DELETE")

    def _register_file(self, path, event_type):
        try:
            stat = os.stat(path)
            size = stat.st_size
            ext = os.path.splitext(path)[1].lower()
            mtime = stat.st_mtime
            upsert_file(path, size, ext, mtime)
            log_access_event(path, event_type)
            print(f"[WATCHER] {event_type}: {path}")
            if self.on_new_file:
                self.on_new_file(path)
        except FileNotFoundError:
            pass


def scan_directory(directory, on_new_file=None):
    print(f"[SCAN] Scanning: {directory}")
    count = 0
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
            except (PermissionError, FileNotFoundError):
                pass
    print(f"[SCAN] Found {count} files in {directory}")
    return count


def start_watcher(directories, on_new_file=None):
    handler = IntentStoreHandler(on_new_file=on_new_file)
    observer = Observer()
    for d in directories:
        if os.path.isdir(d):
            observer.schedule(handler, d, recursive=True)
            print(f"[WATCHER] Watching: {d}")
    observer.start()
    return observer


def stop_watcher(observer):
    observer.stop()
    observer.join()
    print("[WATCHER] Stopped")