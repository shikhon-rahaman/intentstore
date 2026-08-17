from dotenv import load_dotenv
load_dotenv()


import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.database import init_db, get_all_files
from src.collector.file_watcher import scan_directory
from src.engine.semantic_engine import batch_analyze
from src.engine.ebpf_simulator import run_simulation
from src.cli.dashboard import print_banner, cmd_status
from src.logger import get_logger

logger = get_logger("demo")

DEMO_STALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_stale_files")

# (filename, fake age in days) -- gives the demo a realistic spread across
# KEEP / ARCHIVE_SOON / ARCHIVE_NOW instead of everything landing on KEEP
# because every real project file was just edited.
SEED_FILES = [
    ("old_backup_2023.bak", 620),
    ("rotated_service.log", 500),
    ("unused_draft_notes.txt", 400),
    ("legacy_config.tmp", 210),
]


def seed_stale_demo_files():
    """Create a few synthetic old files so the demo shows the full range
    of archival actions, not just KEEP. Purely for demo purposes -- safe
    to delete demo_stale_files/ at any time."""
    os.makedirs(DEMO_STALE_DIR, exist_ok=True)
    now = time.time()
    for filename, age_days in SEED_FILES:
        path = os.path.join(DEMO_STALE_DIR, filename)
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write("Synthetic stale file for hackathon demo purposes.\n")
        old_time = now - (age_days * 86400)
        os.utime(path, (old_time, old_time))
    logger.info("Seeded %d synthetic stale files for demo variety", len(SEED_FILES))


def print_top_recommendations(files, top_n=3):
    ranked = sorted(
        files,
        key=lambda f: f.get("archival_urgency") or 0.0,
        reverse=True,
    )[:top_n]

    logger.info("=" * 62)
    logger.info("  TOP %d ARCHIVAL RECOMMENDATIONS", top_n)
    logger.info("=" * 62)

    if not ranked:
        logger.info("  No files analyzed yet.")
        return

    for i, f in enumerate(ranked, 1):
        fname = os.path.basename(f["path"])
        urgency = f.get("archival_urgency") or 0.0
        rec = f.get("archival_recommendation") or "PENDING"
        summary = f.get("content_summary") or "No summary"
        logger.info("  #%d  %s", i, fname)
        logger.info("      Urgency: %.2f  |  Action: %s", urgency, rec)
        logger.info("      %s", summary)

    logger.info("=" * 62)


def main():
    try:
        print_banner()
        init_db()

        seed_stale_demo_files()

        target = os.path.abspath(".")
        logger.info("Running IntentStore demo on: %s", target)

        scan_directory(target)
        files = get_all_files()
        sample_paths = [f["path"] for f in files[:5]] or [os.path.join(target, "run_demo.py")]

        run_simulation(sample_paths, count=5)

        logger.info("Analyzing %d files...", min(len(files), 20))
        batch_analyze(files[:20])

        class Args:
            path = target
            threshold = "0.6"

        cmd_status(Args())

        updated_files = get_all_files()
        print_top_recommendations(updated_files, top_n=3)
    except Exception as exc:
        logger.error("Demo failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()