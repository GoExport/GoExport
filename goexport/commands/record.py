import argparse
import logging
from pathlib import Path

from goexport import config
from goexport.helpers import add_player_arguments
from goexport.helpers import parse_resolution as parse_resolution
from goexport.services.recorder import RecordingService

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "record",
        help="Export a video with the WYSIWYG screen-recording pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    add_player_arguments(parser)

    parser.add_argument(
        "-id", "--movie-id", help="The ID of the movie to be exported.", required=True
    )

    parser.add_argument(
        "-uid",
        "--user-id",
        help="The ID of the user associated with the movie.",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=sorted(config.SUPPORTED_FORMATS),
        default=config.OUTPUT_FORMAT,
        help="Format of the exported video.",
    )

    parser.add_argument(
        "-out",
        "--output",
        type=Path,
        default=Path("final_output"),
        help="Output video filename (default: final_output)",
    )

    parser.add_argument(
        "--no-outro",
        action="store_true",
        help="Do not append an outro video.",
    )

    parser.add_argument(
        "--use-outro",
        type=Path,
        default=config.OUTRO_PATH,
        help="Path to an outro video to append after recording.",
    )

    parser.set_defaults(
        func=entry,
    )


def entry(args: argparse.Namespace) -> int:
    return record_video(args)


def record_video(args: argparse.Namespace) -> int:
    return RecordingService(args).run()
