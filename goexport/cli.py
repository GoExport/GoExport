import argparse
import logging
import sys
from contextlib import nullcontext, redirect_stdout

from goexport.commands import COMMANDS
from goexport.config import APP_NAME, VERSION
from goexport.log import setup_logging
from goexport.reporting import Reporter

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} {VERSION}")

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

    parser.add_argument(
        "--json",
        action="store_true",
        help="Write newline-delimited JSON events to stdout",
    )

    subparsers = parser.add_subparsers(required=True)

    for command in COMMANDS:
        command.register(subparsers)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    json_mode = bool(getattr(args, "json", False))
    reporter = Reporter(json_mode=json_mode, stream=sys.stdout)
    args.reporter = reporter
    setup_logging(args.verbose, json_mode=json_mode)
    output_context = redirect_stdout(sys.stderr) if json_mode else nullcontext()

    try:
        with output_context:
            return args.func(args)
    except KeyboardInterrupt:
        if json_mode:
            reporter.error("Operation cancelled by user.", 130)
        else:
            logger.warning("Operation cancelled by user.")
        return 130
    except Exception as error:
        if json_mode:
            reporter.error(str(error) or type(error).__name__, 1)
            logger.debug("Unhandled exception.", exc_info=True)
        else:
            logger.exception("Unhandled exception.")
        return 1
