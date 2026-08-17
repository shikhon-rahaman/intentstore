import os
import sys
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from src.database import init_db, get_all_files, get_high_urgency_files, get_stats
from src.collector.file_watcher import scan_directory, start_watcher, stop_watcher
from src.engine.semantic_engine import compute_semantic_access_entropy, batch_analyze
from src.engine.report_generator import generate_report, ARCHIVABLE
from src.logger import get_logger

logger = get_logger("cli")

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.text import Text
    RICH = True
except ImportError:
    RICH = False
    Console = Table = Panel = box = Text = None
    logger.warning("rich not installed — falling back to plain text output")

console = Console() if RICH else None


def print_banner():
    banner = """
==============================================================
  INTENTSTORE — Semantic Storage Intelligence Engine
  CDAC SSM Next-Gen Kernel Hackathon 2026
==============================================================
"""
    logger.info(banner)


def urgency_color(score):
    if score >= 0.8:
        return "red"
    elif score >= 0.6:
        return "yellow"
    elif score >= 0.4:
        return "blue"
    return "green"


def cmd_scan(args):
    print_banner()
    target = os.path.abspath(args.path)
    if not os.path.isdir(target):
        logger.error("Not a directory: %s", target)
        return
    try:
        init_db()
        logger.info("Scanning: %s", target)
        count = scan_directory(target)
        logger.info("Found %d files. Analyzing...", count)
        all_files = get_all_files()
        results = batch_analyze(all_files[:30])
        logger.info("Done. Analyzed %d files.", len(results))
        cmd_status(args)
    except Exception as exc:
        logger.error("Scan failed: %s", exc)


def cmd_status(args):
    try:
        stats = get_stats()
        files = get_all_files()
        if RICH:
            console.print(Panel(
                f"[bold]Files:[/] {stats['total_files']}   "
                f"[bold]Size:[/] {stats['total_size_mb']} MB   "
                f"[bold red]Urgent:[/] {stats['urgent_files']}   "
                f"[bold]Events:[/] {stats['total_events']}",
                title="[bold cyan]IntentStore Dashboard[/]",
                border_style="cyan",
            ))
            table = Table(box=box.ROUNDED, border_style="cyan", show_lines=True)
            table.add_column("File", max_width=30)
            table.add_column("Summary", max_width=35)
            table.add_column("Urgency", justify="center")
            table.add_column("Action", justify="center")
            for f in files[:25]:
                fname = os.path.basename(f["path"])
                summary = (f["content_summary"] or "")[:33]
                urgency = f["archival_urgency"] or 0.0
                rec = f["archival_recommendation"] or "PENDING"
                color = urgency_color(urgency)
                bar = "█" * int(urgency * 10) + "░" * (10 - int(urgency * 10))
                urgency_text = Text(f"{bar} {urgency:.2f}", style=color)
                rec_colors = {
                    "KEEP": "green", "ARCHIVE_SOON": "yellow",
                    "ARCHIVE_NOW": "red", "DELETE": "bold red", "PENDING": "dim",
                }
                table.add_row(fname, summary, urgency_text, Text(rec, style=rec_colors.get(rec, "white")))
            console.print(table)
        else:
            logger.info(
                "Files: %d | Size: %.2f MB | Urgent: %d",
                stats["total_files"], stats["total_size_mb"], stats["urgent_files"],
            )
            for f in files[:20]:
                logger.info(
                    "%-35s %8.2f  %s",
                    os.path.basename(f["path"]),
                    f["archival_urgency"] or 0.0,
                    f["archival_recommendation"] or "PENDING",
                )
    except Exception as exc:
        logger.error("Status display failed: %s", exc)


def cmd_watch(args):
    print_banner()
    target = os.path.abspath(args.path)
    try:
        init_db()
        logger.info("Watching: %s (Ctrl+C to stop)", target)

        def on_new_file(path):
            try:
                stat = os.stat(path)
                result = compute_semantic_access_entropy(path, stat.st_size, stat.st_mtime)
                logger.info(
                    "NEW: %-35s Urgency: %.2f | %s",
                    os.path.basename(path),
                    result["archival_urgency"],
                    result["archival_recommendation"],
                )
            except Exception as exc:
                logger.error("Error processing new file %s: %s", path, exc)

        observer = start_watcher([target], on_new_file=on_new_file)
        if observer is None:
            logger.error("Could not start watcher — is watchdog installed?")
            return
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_watcher(observer)
    except Exception as exc:
        logger.error("Watch mode failed: %s", exc)


def cmd_report(args):
    try:
        files = get_high_urgency_files(threshold=float(args.threshold))
        stats = get_stats()
        logger.info("=== ARCHIVAL REPORT (threshold=%s) ===", args.threshold)
        logger.info("Files needing action: %d of %d total", len(files), stats["total_files"])
        for f in files:
            logger.info(
                "[%.2f] %s — %s",
                f["archival_urgency"],
                f["archival_recommendation"],
                f["path"],
            )
            logger.info("       %s", f["content_summary"] or "No summary")
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)


def cmd_freespace(args):
    try:
        report = generate_report(verbose=not RICH, save=True)
        t = report["totals"]

        if RICH:
            console.print(Panel(
                f"[bold green]Recoverable:[/] {t['archivable_size_mb']} MB "
                f"({t['archivable_files']} files)\n"
                f"[bold]Total tracked:[/] {t['total_size_mb']} MB "
                f"({t['total_files']} files)\n"
                f"[bold yellow]Potential savings:[/] {t['potential_savings_pct']}%",
                title="[bold cyan]IntentStore Free Space Analysis[/]",
                border_style="green",
            ))
            table = Table(box=box.ROUNDED, border_style="green", title="By Recommendation")
            table.add_column("Recommendation", style="bold")
            table.add_column("Files", justify="right")
            table.add_column("Size (MB)", justify="right")
            table.add_column("Recoverable", justify="center")
            for rec, group in report["by_recommendation"].items():
                recoverable = "Yes" if rec in ARCHIVABLE else "No"
                style = "green" if rec in ARCHIVABLE else "dim"
                table.add_row(
                    rec,
                    str(group["file_count"]),
                    f"{group['total_size_mb']:.2f}",
                    Text(recoverable, style=style),
                )
            console.print(table)
            console.print("[dim]Full report saved to reports/latest_report.json[/]")
    except Exception as exc:
        logger.error("Freespace analysis failed: %s", exc)


def main():
    parser = argparse.ArgumentParser(description="IntentStore - Semantic Storage Intelligence")
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="Scan and analyze a directory")
    p_scan.add_argument("path", help="Directory path")
    p_scan.set_defaults(func=cmd_scan)

    p_status = sub.add_parser("status", help="Show dashboard")
    p_status.add_argument("path", nargs="?", default=".")
    p_status.set_defaults(func=cmd_status)

    p_watch = sub.add_parser("watch", help="Live watch mode")
    p_watch.add_argument("path", help="Directory path")
    p_watch.set_defaults(func=cmd_watch)

    p_report = sub.add_parser("report", help="Archival report")
    p_report.add_argument("--threshold", default="0.6")
    p_report.set_defaults(func=cmd_report)

    p_freespace = sub.add_parser("freespace", help="Show recoverable storage savings")
    p_freespace.set_defaults(func=cmd_freespace)

    args = parser.parse_args()
    if not args.command:
        print_banner()
        parser.print_help()
        return
    try:
        args.func(args)
    except Exception as exc:
        logger.error("Command failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
