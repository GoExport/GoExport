import argparse
from math import gcd

from goexport.models.export import ExportSettings
from goexport.config import SUPPORTED_FORMATS

def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "export",
        help="Export a GoAnimate video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default=ExportSettings.output_format,
    )

    parser.add_argument(
        "-r",
        "--resolution",
        type=parse_resolution,
        default=(ExportSettings.width, ExportSettings.height),
    )

    parser.add_argument(
        "--no-wide",
        action="store_false",
        dest="is_wide",
        help="Disable GoAnimate widescreen mode.",
    )

    parser.set_defaults(
        func=entry,
        is_wide=True,
    )


def parse_resolution(value: str) -> tuple[int, int]:
    try:
        width, height = map(int, value.lower().split("x"))

        if width <= 0 or height <= 0:
            raise ValueError

        return width, height

    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Resolution must be in the format WIDTHxHEIGHT "
            f"(e.g., 1920x1080), got '{value}'."
        )


def calculate_aspect_ratio(width: int, height: int) -> tuple[int, int]:
    common_divisor = gcd(width, height)
    return (
        width // common_divisor,
        height // common_divisor,
    )


def entry(args: argparse.Namespace) -> int:
    width, height = args.resolution

    settings = ExportSettings(
        width=width,
        height=height,
        output_format=args.format,
        is_wide=args.is_wide,
    )

    # return export_video(settings) Not implemented

    return 0