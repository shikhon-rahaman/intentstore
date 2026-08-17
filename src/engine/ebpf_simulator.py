import os
import sys
import random
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from src.database import log_access_event
from src.logger import get_logger

logger = get_logger("ebpf")

SYSCALL_TYPES = ("openat", "read", "write")
PROCESS_NAMES = ("python", "node", "bash", "sshd", "nginx", "vim")


def _format_timestamp(ts=None):
    ts = ts or time.time()
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def simulate_syscall_event(file_path, syscall=None, pid=None, process_name=None):
    """Simulate a single eBPF syscall trace event."""
    try:
        syscall = syscall or random.choice(SYSCALL_TYPES)
        pid = pid or random.randint(1000, 65535)
        process_name = process_name or random.choice(PROCESS_NAMES)
        ts = time.time()

        event = {
            "syscall": syscall,
            "pid": pid,
            "timestamp": ts,
            "timestamp_str": _format_timestamp(ts),
            "filepath": file_path,
            "process_name": process_name,
        }

        log_access_event(file_path, syscall.upper(), process_name)
        return event
    except Exception as exc:
        logger.error("Failed to simulate syscall for %s: %s", file_path, exc)
        return None


def format_event(event):
    return (
        f"PID={event['pid']:<6} "
        f"{event['syscall']:<7} "
        f"{event['filepath']}"
    )


def run_simulation(file_paths, count=5, verbose=True):
    """Simulate eBPF syscall tracing for demo purposes."""
    if not file_paths:
        file_paths = ["/tmp/example.dat"]

    events = []
    syscalls = ["openat", "read", "write", "read", "write"]

    if verbose:
        logger.info("Simulating kernel syscall trace (SSM Next-Gen Kernel)")
        logger.info("Attaching probe: tracepoint/syscalls/sys_enter_*")
        logger.info("-" * 72)

    for i in range(min(count, len(syscalls))):
        fpath = file_paths[i % len(file_paths)]
        try:
            event = simulate_syscall_event(fpath, syscall=syscalls[i])
            if event:
                events.append(event)
                if verbose:
                    logger.info("%s  %s", event["timestamp_str"], format_event(event))
            time.sleep(0.05)
        except Exception as exc:
            logger.error("Simulation step %d failed: %s", i + 1, exc)

    if verbose:
        logger.info("-" * 72)
        logger.info("Captured %d syscall events", len(events))

    return events
