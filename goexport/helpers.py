import argparse
import sys
from math import gcd
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from goexport import config
from goexport.player_options import parse_flashvars, parse_replacement


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


def non_negative_seconds(value: str) -> int:
    try:
        seconds = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"Expected a whole number of seconds, got '{value}'."
        ) from error
    if seconds < 0:
        raise argparse.ArgumentTypeError("Seconds cannot be negative.")
    return seconds


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


class ConfirmationDeclined(RuntimeError):
    """A change needed approval that was refused or could not be requested."""


def interactive_terminal() -> bool:
    return bool(sys.stdin.isatty() and sys.stdout.isatty())


def require_confirmation(
    args: argparse.Namespace, question: str, details: list[str]
) -> None:
    """Ask before a system change unless ``--yes`` was given.

    JSON mode and non-interactive sessions cannot be prompted, so they fail
    instead of waiting for input that will never arrive.
    """
    if getattr(args, "yes", False):
        return
    if getattr(args, "json", False) or not interactive_terminal():
        raise ConfirmationDeclined(
            "This change needs confirmation, and GoExport cannot prompt for it "
            "here. Re-run with -y or --yes to approve it."
        )
    console = Console()
    for line in details:
        console.print(line, markup=False, highlight=False)
    console.print()
    if not Confirm.ask(question, default=False, console=console):
        raise ConfirmationDeclined("Cancelled; nothing was changed.")


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
        "-uid",
        "--user-id",
        help="The ID of the user associated with the movie.",
    )

    parser.add_argument(
        "--additional-flashvars",
        type=parse_flashvars,
        default={},
        metavar="NAME=VALUE&NAME=VALUE",
        help="Add Flashvars or override the player's standard Flashvars.",
    )

    parser.add_argument(
        "--replacement",
        action="append",
        type=parse_replacement,
        default=[],
        metavar="NAME=VALUE",
        help="Add or override a configured player placeholder replacement.",
    )

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
        default=config.IS_WIDE,
        help="Disable GoAnimate widescreen mode.",
    )

    parser.add_argument(
        "--electron",
        action="store_true",
        default=config.ELECTRON,
        help=(
            "When you want to hook into Electron browsers instead of a separate "
            "browser, useful for Wrapper Offline integration."
        ),
    )

    parser.add_argument(
        "-nft",
        "--no-flash-timeout",
        action="store_true",
        help="Wait indefinitely for the Flash player to load.",
    )

    parser.add_argument(
        "--verification-timeout",
        type=non_negative_seconds,
        default=config.VERIFICATION_TIMEOUT,
        metavar="SECONDS",
        help=(
            "Seconds to wait for Cloudflare or Anubis verification in the "
            "browser (0 waits indefinitely)."
        ),
    )

    parser.add_argument(
        "--automatic-verification-timeout",
        type=non_negative_seconds,
        default=config.VERIFICATION_AUTOMATIC_TIMEOUT,
        metavar="SECONDS",
        help=(
            "Seconds an automatic Anubis check may run before the browser is "
            "shown for manual verification (0 keeps waiting until "
            "--verification-timeout)."
        ),
    )

    parser.add_argument(
        "--no-interactive-verification",
        action="store_false",
        dest="interactive_verification",
        default=config.VERIFICATION_INTERACTIVE,
        help=(
            "Fail instead of showing the browser when a Cloudflare or Anubis "
            "challenge requires manual verification."
        ),
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

    add_runtime_arguments(parser)


def add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    """Register paths for the external runtime binaries."""
    parser.add_argument(
        "--chrome-path",
        type=existing_file,
        default=config.CHROME_PATH,
        help="Path to the Chromium executable.",
    )
    parser.add_argument(
        "--chromedriver-path",
        type=existing_file,
        default=config.CHROMEDRIVER_PATH,
        help="Path to the ChromeDriver executable.",
    )
    parser.add_argument(
        "--flash-plugin-path",
        type=existing_file,
        default=config.FLASH_PLUGIN_PATH,
        help="Path to the Pepper Flash plugin.",
    )
    parser.add_argument(
        "--flash-plugin-version",
        default=config.FLASH_PLUGIN_VERSION,
        help="Pepper Flash plugin version passed to Chromium.",
    )
    parser.add_argument(
        "--ffmpeg-path",
        type=existing_file,
        default=config.FFMPEG_PATH,
        help="Path to the FFmpeg executable.",
    )
