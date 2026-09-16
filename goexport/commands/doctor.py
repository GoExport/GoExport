import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "doctor",
        help="Troubleshooting command.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )