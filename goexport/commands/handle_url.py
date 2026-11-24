"""Handle goexport:// URLs opened through the registered URL protocol."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime

from goexport import config
from goexport.commands import record
from goexport.dependencies import DependencyManager
from goexport.helpers import require_confirmation
from goexport.reporting import get_reporter
from goexport.url_request import parse_request

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "handle-url",
        help="Run a goexport:// request (used by the registered URL protocol).",
        description=(
            "Validate a goexport:// URL, show what it requests, and run it with "
            "the record command after confirmation."
        ),
    )
    parser.add_argument(
        "url", help="The goexport:// URL, for example goexport://record?movie_id=123."
    )
    parser.set_defaults(func=entry, pause_on_exit=True)


def build_record_arguments(
    args: argparse.Namespace, record_argv: list[str]
) -> argparse.Namespace:
    """Parse ``record_argv`` with the real ``record`` command definition."""
    parser = argparse.ArgumentParser(prog="GoExport")
    record.register(parser.add_subparsers(required=True))
    record_args = parser.parse_args(["record", *record_argv])
    for name in ("reporter", "yes", "json", "verbose"):
        setattr(record_args, name, getattr(args, name, None))
    return record_args


def entry(args: argparse.Namespace) -> int:
    reporter = get_reporter(args)
    request = parse_request(args.url)
    output = request.output_path(
        config.PROTOCOL_OUTPUT_DIR, datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    record_args = build_record_arguments(args, request.record_arguments(output))

    width = max(len(label) for label, _ in request.summary())
    require_confirmation(
        args,
        "Start this recording?",
        [
            "A goexport:// link asked GoExport to record a video.",
            "Only continue if you opened this link and trust these servers:",
            "",
            *(f"  {label.ljust(width)}  {value}" for label, value in request.summary()),
            f"  {'Output'.ljust(width)}  {output}.{record_args.format}",
        ],
    )
    reporter.diagnostic(
        logging.INFO, "Starting the requested recording.", logger=logger
    )
    DependencyManager().bootstrap(record_args, record_args.runtime_dependencies)
    return record_args.func(record_args)
