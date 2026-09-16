"""Human-readable and machine-readable command reporting."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, TextIO


class Reporter:
    """Report command events as logs or newline-delimited JSON."""

    def __init__(self, json_mode: bool = False, stream: TextIO | None = None):
        self.json_mode = json_mode
        self.stream = stream if stream is not None else sys.stdout
        self._last_progress: float | None = None

    def _emit(self, event: dict[str, Any]) -> None:
        print(json.dumps(event, separators=(",", ":")), file=self.stream, flush=True)

    def progress(self, progress: float, stage: str) -> None:
        # Completion owns 100 so consumers never see a finished percentage
        # while cleanup or post-processing can still fail.
        value = max(0.0, min(99.0, float(progress)))
        if self._last_progress is not None and value < self._last_progress:
            value = self._last_progress
        # Long movies can contain thousands of frames. One update per whole
        # percentage keeps the live protocol useful without flooding it.
        if self._last_progress is not None and value - self._last_progress < 1:
            return
        self._last_progress = value
        if self.json_mode:
            self._emit({"event": "progress", "progress": value, "stage": stage})
        else:
            logging.getLogger("goexport.progress").info(
                "%s: %.2f%%", stage.replace("_", " ").title(), value
            )

    def complete(self, output: str | Path) -> None:
        self._last_progress = 100.0
        event = {"event": "complete", "progress": 100, "output": str(output)}
        if self.json_mode:
            self._emit(event)
        else:
            logging.getLogger("goexport.progress").info(
                "Complete: 100.00%% (%s)", output
            )

    def error(self, message: str, code: int = 1) -> None:
        if self.json_mode:
            self._emit({"event": "error", "message": message, "code": code})
        else:
            logging.getLogger("goexport.cli").error(message)

    def result(self, **fields: Any) -> None:
        if self.json_mode:
            self._emit({"event": "result", **fields})

    def diagnostic(
        self, level: int, message: str, *args: object, logger: logging.Logger
    ) -> None:
        """Write human-facing command detail only in normal mode."""
        if not self.json_mode:
            logger.log(level, message, *args)


def get_reporter(args: object) -> Reporter:
    """Return the CLI reporter, with a normal-mode fallback for direct callers."""
    reporter = getattr(args, "reporter", None)
    return reporter if isinstance(reporter, Reporter) else Reporter()
