import os
import sys

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
