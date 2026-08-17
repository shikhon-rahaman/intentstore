import os
import sys
import json
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from src.database import get_all_files, get_stats
from src.logger import get_logger

logger = get_logger("report")

ARCHIVABLE = {"ARCHIVE_NOW", "ARCHIVE_SOON", "DELETE"}
REPORT_DIR = os.path.join(os.path.dirname(__file__), "../../reports")
REPORT_PATH = os.path.join(REPORT_DIR, "latest_report.json")


def _bytes_to_mb(size_bytes):
    return round(size_bytes / (1024 * 1024), 2)


def _file_entry(f):
    return {
        "path": f["path"],
        "size_bytes": f.get("size_bytes") or 0,
        "size_mb": _bytes_to_mb(f.get("size_bytes") or 0),
        "archival_urgency": f.get("archival_urgency") or 0.0,
        "archival_recommendation": f.get("archival_recommendation") or "PENDING",
        "content_summary": f.get("content_summary") or "",
    }


def build_report():
    try:
        files = get_all_files()
        stats = get_stats()

        groups = defaultdict(list)
        for f in files:
            rec = f.get("archival_recommendation") or "PENDING"
            groups[rec].append(_file_entry(f))

        total_bytes = sum(f.get("size_bytes") or 0 for f in files)
        archivable_bytes = sum(
            f.get("size_bytes") or 0
            for f in files
            if (f.get("archival_recommendation") or "PENDING") in ARCHIVABLE
        )
        keep_bytes = sum(
            f.get("size_bytes") or 0
            for f in files
            if (f.get("archival_recommendation") or "PENDING") == "KEEP"
        )

        grouped_summary = {}
        for rec, entries in sorted(groups.items()):
            group_size = sum(e["size_bytes"] for e in entries)
            grouped_summary[rec] = {
                "file_count": len(entries),
                "total_size_bytes": group_size,
                "total_size_mb": _bytes_to_mb(group_size),
                "files": entries,
            }

        savings_pct = round((archivable_bytes / total_bytes * 100), 1) if total_bytes else 0.0

        return {
            "generated_at": datetime.now().isoformat(),
            "stats": stats,
            "totals": {
                "total_files": len(files),
                "total_size_bytes": total_bytes,
                "total_size_mb": _bytes_to_mb(total_bytes),
                "archivable_files": sum(
                    1 for f in files
                    if (f.get("archival_recommendation") or "PENDING") in ARCHIVABLE
                ),
                "archivable_size_bytes": archivable_bytes,
                "archivable_size_mb": _bytes_to_mb(archivable_bytes),
                "keep_size_bytes": keep_bytes,
                "keep_size_mb": _bytes_to_mb(keep_bytes),
                "potential_savings_pct": savings_pct,
            },
            "by_recommendation": grouped_summary,
        }
    except Exception as exc:
        logger.error("Failed to build report: %s", exc)
        return {
            "generated_at": datetime.now().isoformat(),
            "stats": {},
            "totals": {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "archivable_files": 0,
                "archivable_size_bytes": 0,
                "archivable_size_mb": 0.0,
                "keep_size_bytes": 0,
                "keep_size_mb": 0.0,
                "potential_savings_pct": 0.0,
            },
            "by_recommendation": {},
        }


def format_report_text(report):
    t = report["totals"]
    lines = [
        "",
        "=" * 62,
        "  INTENTSTORE STORAGE SAVINGS REPORT",
        "=" * 62,
        f"  Generated: {report['generated_at']}",
        "",
        f"  Total tracked:  {t['total_files']} files  ({t['total_size_mb']} MB)",
        f"  Can archive:    {t['archivable_files']} files  ({t['archivable_size_mb']} MB)",
        f"  Potential savings: {t['potential_savings_pct']}% of tracked storage",
        "",
        "  Breakdown by recommendation:",
        "  " + "-" * 56,
    ]

    for rec, group in report["by_recommendation"].items():
        marker = "  <-- recoverable" if rec in ARCHIVABLE else ""
        lines.append(
            f"  {rec:<16} {group['file_count']:>4} files  "
            f"{group['total_size_mb']:>8.2f} MB{marker}"
        )

    lines += [
        "  " + "-" * 56,
        f"  Report saved to: {REPORT_PATH}",
        "=" * 62,
        "",
    ]
    return "\n".join(lines)


def save_report(report, path=REPORT_PATH):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Report saved to %s", path)
        return path
    except OSError as exc:
        logger.error("Failed to save report to %s: %s", path, exc)
        return None


def generate_report(verbose=True, save=True):
    report = build_report()
    if save:
        save_report(report)
    if verbose:
        for line in format_report_text(report).splitlines():
            logger.info(line)
    return report
