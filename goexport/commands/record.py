import argparse
import logging
from pathlib import Path

from goexport import config
from goexport.helpers import add_player_arguments
from goexport.helpers import parse_resolution as parse_resolution
from goexport.services.recorder import RecordingService
from goexport.services.recording_backends import (
    PYSCAP_MIGRATION_MESSAGE,
    RECORDING_BACKENDS,
)
from goexport.services.recording_backends.capturekit import AUDIO_MODES

logger = logging.getLogger(__name__)


def parse_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("OBS port must be an integer") from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("OBS port must be between 1 and 65535")
    return port


def parse_capture_backend(value: str) -> str:
    if value == "pyscap":
        raise argparse.ArgumentTypeError(PYSCAP_MIGRATION_MESSAGE)
    return value


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

    parser.add_argument(
        "--capture-backend",
        type=parse_capture_backend,
        choices=RECORDING_BACKENDS,
        default=config.RECORDING_BACKEND,
        help=(
            "Screen-recording backend: CaptureKit (Windows and Linux X11/Xvfb) "
            "or OBS Studio."
        ),
    )
    parser.add_argument(
        "--capturekit-audio",
        choices=AUDIO_MODES,
        default=config.CAPTUREKIT_AUDIO,
        help=(
            "Audio recorded by the CaptureKit backend: 'process' records only "
            "this export's Chromium, 'system' records everything played on the "
            "default output device, 'none' records silent video."
        ),
    )
    parser.add_argument(
        "--capturekit-encoder",
        default=config.CAPTUREKIT_ENCODER,
        help=(
            "H.264 encoder for the CaptureKit backend: 'auto' validates NVENC, "
            "QSV and AMF before falling back to libx264, or name an FFmpeg "
            "encoder such as libx264."
        ),
    )
    parser.add_argument(
        "--obs-host",
        default=config.OBS_HOST,
        help="OBS WebSocket host (OBS backend only).",
    )
    parser.add_argument(
        "--obs-port",
        type=parse_port,
        default=config.OBS_PORT,
        help="OBS WebSocket port (OBS backend only).",
    )
    parser.add_argument(
        "--obs-profile",
        default=config.OBS_PROFILE,
        help="Persistent GoExport-owned OBS profile.",
    )
    parser.add_argument(
        "--obs-scene-collection",
        default=config.OBS_SCENE_COLLECTION,
        help="Persistent GoExport-owned OBS scene collection.",
    )
    parser.add_argument(
        "--obs-force-profile",
        action="store_true",
        help=(
            "Allow GoExport to reuse and reconfigure an existing OBS profile and "
            "scene collection even when they are not marked as GoExport-owned."
        ),
    )

    parser.set_defaults(
        func=entry,
        runtime_dependencies=("chromium", "chromedriver", "pepper_flash", "ffmpeg"),
    )


def entry(args: argparse.Namespace) -> int:
    return record_video(args)


def record_video(args: argparse.Namespace) -> int:
    return RecordingService(args).run()
