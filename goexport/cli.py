import argparse
import logging

from goexport.commands import COMMANDS
from goexport.config import APP_NAME, VERSION
from goexport.log import setup_logging

logger = logging.getLogger(__name__)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} {VERSION}"
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{APP_NAME} {VERSION}",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(required=True)

    for command in COMMANDS:
        command.register(subparsers)

    return parser


def main() -> int:
    args = build_parser().parse_args()

    setup_logging(args.verbose)

    try:
        return args.func(args)
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user.")
        return 130
    except Exception:
        logger.exception("Unhandled exception.")
        return 1