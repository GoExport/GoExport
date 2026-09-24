#!/usr/bin/env python3
"""Developer/build entry point for GoExport's shared dependency manager."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from goexport.dependencies import DependencyManager  # noqa: E402
from goexport.dependencies.definitions import DOWNLOADS  # noqa: E402
from goexport.dependencies.installers import make_executable  # noqa: E402
from goexport.log import setup_logging  # noqa: E402

__all__ = ["DOWNLOADS", "make_executable"]


def main() -> int:
    setup_logging()
    logging.getLogger(__name__).info("GoExport dependency installer")
    DependencyManager().install_all()
    logging.getLogger(__name__).info("All dependencies are installed and healthy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
