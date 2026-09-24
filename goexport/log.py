import logging

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(verbose: bool = False, json_mode: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=Console(stderr=json_mode),
                rich_tracebacks=True,
                markup=True,
                show_path=False,
            )
        ],
        force=True,
    )
    # httpx logs complete redirected URLs at INFO, including temporary signed
    # release-asset query parameters. GoExport reports download stages itself.
    logging.getLogger("httpx").setLevel(logging.WARNING)
