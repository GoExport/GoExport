import argparse
import logging
from math import gcd

from goexport.config import SUPPORTED_FORMATS, CHROME_PATH, CHROMEDRIVER_PATH, FFMPEG_PATH, FLASH_PLUGIN_PATH, PATH_FLASH_VERSION_WINDOWS, TEMPLATE_HTML_PATH
from goexport.models.export import ExportSettings

from goexport.services.browser import BrowserService

logger = logging.getLogger(__name__)

DEFAULT_EXPORT_SETTINGS = ExportSettings()


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
        default=DEFAULT_EXPORT_SETTINGS.output_format,
        help="Format of the exported video.",
    )

    parser.add_argument(
        "-r",
        "--resolution",
        type=parse_resolution,
        default=(
            DEFAULT_EXPORT_SETTINGS.width,
            DEFAULT_EXPORT_SETTINGS.height,
        ),
        help="Resolution of the exported video (e.g., 1920x1080).",
    )

    parser.add_argument(
        "-u",
        "--url",
        default=DEFAULT_EXPORT_SETTINGS.url,
        help="The URL of the Wrapper: Offline instance.",
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
        url=args.url,
    )

    return export_video(settings)


def export_video(settings: ExportSettings) -> int:
    # Calculate aspect ratio
    aspect_ratio = calculate_aspect_ratio(settings.width, settings.height)

    # Open web browser
    browser_service = BrowserService(
        chrome_path=CHROME_PATH,
        chromedriver_path=CHROMEDRIVER_PATH,
        flash_path=FLASH_PLUGIN_PATH,
        flash_version=PATH_FLASH_VERSION_WINDOWS,
    )

    driver = browser_service.create_driver()

    driver.get(settings.url)

    browser_service.set_viewport_size(
        driver, settings.width, settings.height
    )

    browser_service.enable_flash(driver)

    browser_service.inject_dom(driver, TEMPLATE_HTML_PATH, {
        "PLAYER_WIDTH": settings.width,
        "PLAYER_HEIGHT": settings.height,
    })

    import time
    time.sleep(10)

    return 0