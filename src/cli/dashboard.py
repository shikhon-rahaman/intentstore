import os
import sys
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from src.database import init_db, get_all_files, get_high_urgency_files, get_stats
from src.collector.file_watcher import scan_directory, start_watcher, stop_watcher
from src.engine.semantic_engine import compute_semantic_access_entropy, batch_analyze

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.text import Text
    RICH = True
except ImportError:
    RICH = False

console = Console() if RICH else None

def print_banner():
    print("""
==============================================================
  INTENTSTORE — Semantic Storage Intelligence Engine
  CDAC SSM Next-Gen Kernel Hackathon 2026
==============================================================
""")

def urgency_color(score):
    if score >= 0.8: return "red"
    elif score >= 0.6: return "yellow"
    elif score >= 0.4: return "blue"
    return "green"

def cmd_scan(args):
    print_banner()
    target = os.path.abspath(args.path)
    if not os.path.isdir(target):
        print(f"ERROR: Not a directory: {target}")
        return
    init_db()
    print(f"Scanning: {target}\n")
    count = scan_directory(target)
    print(f"\nFound {count} files. Analyzing...\n")
    all_files = get_all_files()
    results = batch_analyze(all_files[:30])
    print(f"\nDone. Analyzed {len(results)} files.\n")
    cmd_status(args)

def cmd_status(args):
    stats = get_stats()
    files = get_all_files()
    if RICH:
        console.print(Panel(
            f"[bold]Files:[/] {stats['total_files']}   "
            f"[bold]Size:[/] {stats['total_size_mb']} MB   "
            f"[bold red]Urgent:[/] {stats['urgent_files']}   "
            f"[bold]Events:[/] {stats['total_events']}",
            title="[bold cyan]IntentStore Dashboard[/]",
            border_style="cyan"
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
                "ARCHIVE_NOW": "red", "DELETE": "bold red", "PENDING": "dim"
            }
            table.add_row(fname, summary, urgency_text, Text(rec, style=rec_colors.get(rec, "white")))
        console.print(table)
    else:
        print(f"Files: {stats['total_files']} | Size: {stats['total_size_mb']} MB | Urgent: {stats['urgent_files']}")
        print(f"\n{'FILE':<35} {'URGENCY':<8} {'ACTION'}")
        print("-" * 70)
        for f in files[:20]:
            print(f"{os.path.basename(f['path']):<35} {f['archival_urgency']:<8.2f} {f['archival_recommendation'] or 'PENDING'}")

def cmd_watch(args):
    print_banner()
    target = os.path.abspath(args.path)
    init_db()
    print(f"Watching: {target} (Ctrl+C to stop)\n")
    def on_new_file(path):
        try:
            stat = os.stat(path)
            result = compute_semantic_access_entropy(path, stat.st_size, stat.st_mtime)
            urgency = result["archival_urgency"]
            print(f"NEW: {os.path.basename(path):<35} Urgency: {urgency:.2f} | {result['archival_recommendation']}")
        except Exception as e:
            print(f"Error: {e}")
    observer = start_watcher([target], on_new_file=on_new_file)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_watcher(observer)

def cmd_report(args):
    files = get_high_urgency_files(threshold=float(args.threshold))
    stats = get_stats()
    print(f"\n=== ARCHIVAL REPORT (threshold={args.threshold}) ===")
    print(f"Files needing action: {len(files)} of {stats['total_files']} total\n")
    for f in files:
        print(f"[{f['archival_urgency']:.2f}] {f['archival_recommendation']} — {f['path']}")
        print(f"       {f['content_summary'] or 'No summary'}\n")

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

    args = parser.parse_args()
    if not args.command:
        print_banner()
        parser.print_help()
        return
    args.func(args)

if __name__ == "__main__":
    main()