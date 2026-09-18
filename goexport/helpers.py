import argparse
from math import gcd
from pathlib import Path

from goexport import config


def parse_resolution(value: str) -> tuple[int, int]:
    try:
        width, height = map(int, value.lower().split("x"))

        if width <= 0 or height <= 0:
            raise ValueError

        return width, height

    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Resolution must be in the format WIDTHxHEIGHT "
            f"(e.g., 1920x1080), got '{value}'."
        ) from exc


def existing_file(path: str) -> Path:
    file_path = Path(path)

    if not file_path.is_file():
        raise argparse.ArgumentTypeError(f"'{path}' does not exist or is not a file.")

    return file_path


def existing_directory(path: str) -> Path:
    dir_path = Path(path)

    if not dir_path.is_dir():
        raise argparse.ArgumentTypeError(
            f"'{path}' does not exist or is not a directory."
        )

    return dir_path


def calculate_aspect_ratio(width: int, height: int) -> tuple[int, int]:
    common_divisor = gcd(width, height)

    return (
        width // common_divisor,
        height // common_divisor,
    )


def resolve_output_path(output: Path, video_format: str) -> Path:
    if output.suffix.lower() != f".{video_format}":
        final_output_path = Path(f"{output}.{video_format}")
    else:
        final_output_path = output

    final_output_path.parent.mkdir(parents=True, exist_ok=True)

    return final_output_path


def add_player_arguments(parser: argparse.ArgumentParser) -> None:
    """Register player settings shared by recording and frame-by-frame export."""
    parser.add_argument(
        "-r",
        "--resolution",
        type=parse_resolution,
        default=(
            config.WIDTH,
            config.HEIGHT,
        ),
        help="Resolution of the exported video (e.g., 1920x1080).",
    )

    parser.add_argument(
        "--no-wide",
        action="store_false",
        dest="is_wide",
        help="Disable GoAnimate widescreen mode.",
    )

    parser.add_argument(
        "-u",
        "--url",
        default=config.URL,
        help="The URL of the Wrapper: Offline instance.",
    )

    parser.add_argument(
        "-api",
        "--api-url",
        default=config.API_URL,
        help="The URL of the Wrapper: Offline API instance.",
    )

    parser.add_argument(
        "-swf",
        "--swf-url",
        default=config.SWF_URL,
        help="The URL of the SWF file to be used in the export.",
    )

    parser.add_argument(
        "-store",
        "--store-path",
        default=config.STORE_PATH,
        help="The URL of the store path to be used in the export.",
    )

    parser.add_argument(
        "-theme",
        "--client-theme-path",
        default=config.CLIENT_THEME_PATH,
        help="The URL of the client theme path to be used in the export.",
    )

    parser.add_argument("--chrome-path", type=existing_file, default=config.CHROME_PATH,
                        help="Path to the Chromium executable.")
    parser.add_argument("--chromedriver-path", type=existing_file, default=config.CHROMEDRIVER_PATH,
                        help="Path to the ChromeDriver executable.")
    parser.add_argument("--flash-plugin-path", type=existing_file, default=config.FLASH_PLUGIN_PATH,
                        help="Path to the Pepper Flash plugin.")
    parser.add_argument("--ffmpeg-path", type=existing_file, default=config.FFMPEG_PATH,
                        help="Path to the FFmpeg executable.")
