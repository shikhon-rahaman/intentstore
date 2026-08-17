import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.database import init_db
from src.collector.file_watcher import scan_directory
from src.engine.semantic_engine import batch_analyze
from src.database import get_all_files
from src.cli.dashboard import print_banner, cmd_status
import argparse

print_banner()
init_db()

target = os.path.abspath(".")
print(f"Running IntentStore demo on: {target}\n")

scan_directory(target)
files = get_all_files()
print(f"\nAnalyzing {min(len(files), 20)} files...\n")
batch_analyze(files[:20])

class Args:
    path = target
    threshold = "0.6"

cmd_status(Args())