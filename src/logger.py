import logging
import sys

_CONFIGURED = False


def setup_logging(level=logging.INFO):
    global _CONFIGURED
    if _CONFIGURED:
        return logging.getLogger("intentstore")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    ))

    root = logging.getLogger("intentstore")
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(handler)

    _CONFIGURED = True
    return root


def get_logger(name):
    setup_logging()
    return logging.getLogger(f"intentstore.{name}")
