import argparse
import logging
from pathlib import Path

from goexport import config
from goexport.helpers import add_player_arguments, existing_directory, existing_file
from goexport.helpers import calculate_aspect_ratio as calculate_aspect_ratio
from goexport.helpers import parse_resolution as parse_resolution
from goexport.player_options import build_player_replacements, replacement_overrides
from goexport.reporting import get_reporter
from goexport.services.asset_resolver import AssetResolver
from goexport.services.audio import AudioProcessor
from goexport.services.browser import BrowserService
from goexport.services.ffmpeg import FFmpegAudioEncoder, FFmpegMuxer, FFmpegVideoEncoder
from goexport.services.flash import await_started
from goexport.services.renderer import Renderer
from goexport.services.timeline_builder import TimelineBuilder

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "export",
        help="Export a video with the frame-by-frame rendering pipeline. (ALPHA)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=sorted(config.SUPPORTED_FORMATS),
        default=config.OUTPUT_FORMAT,
        help="Format of the exported video.",
    )

    add_player_arguments(parser)

    parser.add_argument(
        "-id",
        "--movie-id",
        help="The ID of the movie to be exported.",
    )

    parser.add_argument(
        "-xml",
        "--movie-xml",
        type=existing_file,
        help="The path to the movie XML file.",
    )

    parser.add_argument(
        "-ugc",
        "--ugc-path",
        type=existing_directory,
        required=True,
        help="The path to the folder containing UGC assets.",
    )

    parser.add_argument(
        "-as",
        "--assets",
        type=existing_directory,
        required=True,
        help="The path to the folder containing theme assets (The files located inside of 3a981f5cb2739137).",
    )

    parser.set_defaults(
        func=entry,
    )


def entry(args: argparse.Namespace) -> int:
    return export_video(args)


def export_video(args: argparse.Namespace) -> int:
    reporter = get_reporter(args)
    reporter.progress(0, "preparing")
    resolver = AssetResolver(
        args.ugc_path,
        args.assets,
    )

    audio_encoder = FFmpegAudioEncoder(
        ffmpeg_path=args.ffmpeg_path,
        resolver=resolver,
        fps=config.FPS,
    )

    muxer = FFmpegMuxer(args.ffmpeg_path)

    audio_processor = AudioProcessor(
        audio_encoder,
    )

    if args.movie_xml is None:
        raise FileNotFoundError("No movie XML file was provided.")

    timeline_builder = TimelineBuilder(args.movie_xml)

    browser_service = BrowserService(
        chrome_path=args.chrome_path,
        chromedriver_path=args.chromedriver_path,
        flash_path=args.flash_plugin_path,
        flash_version=args.flash_plugin_version,
        electron=getattr(args, "electron", config.ELECTRON),
        width=args.resolution[0],
        height=args.resolution[1],
    )

    try:
        driver = browser_service.create_driver()

        driver.get(args.url)

        browser_service.enter_fullscreen(driver)
        browser_service.validate_screen_resolution(driver)
        browser_service.assert_full_resolution()

        browser_service.enable_flash(driver)

        player_values = {
            "WINDOW_TITLE": "GoExport Export",
            "PLAYER_WIDTH": args.resolution[0],
            "PLAYER_HEIGHT": args.resolution[1],
            "PLAYER_SWF_URL": args.swf_url,
            "IS_WIDE": str(args.is_wide).lower(),
            "API_SERVER": args.api_url,
            "STORE_PATH": args.store_path,
            "CLIENT_THEME_PATH": args.client_theme_path,
            "MOVIE_ID": args.movie_id,
            "MOVIE_XML": str(args.movie_xml),
            "USER_ID": getattr(args, "user_id", None),
        }
        browser_service.inject_dom(
            driver,
            config.TEMPLATE_HTML_PATH,
            build_player_replacements(
                player_values,
                getattr(args, "additional_flashvars", {}),
                {
                    "user_id": getattr(args, "user_id", None),
                    "movie_id": args.movie_id,
                },
                config.PLACEHOLDER_REPLACEMENTS,
                replacement_overrides(getattr(args, "replacement", [])),
            ),
        )

        await_started(
            driver,
            timeout_minutes=0 if getattr(args, "no_flash_timeout", False) else 30,
        )

        encoder = FFmpegVideoEncoder(
            ffmpeg_path=args.ffmpeg_path,
            output_file="output.mkv",
            width=args.resolution[0],
            height=args.resolution[1],
            fps=config.FPS,
        )

        renderer = Renderer(
            driver=driver,
            encoder=encoder,
            resolution_guard=browser_service.assert_full_resolution,
            progress_callback=lambda progress: reporter.progress(
                5 + progress * 0.79, "rendering"
            ),
        )

        reporter.progress(5, "rendering")
        renderer.render()
        reporter.progress(85, "audio")
        timeline = timeline_builder.build()
        audio = audio_processor.process(timeline, renderer.duration_frames)
        reporter.progress(92, "muxing")
        muxer.mux(
            video_file=Path("output.mkv"),
            audio_file=audio,
            output_file=Path(f"final_output.{args.format}"),
        )
        reporter.progress(99, "finalizing")

    finally:
        browser_service.close()

    reporter.complete(Path(f"final_output.{args.format}"))
    return 0
