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

    def verification_required(
        self,
        provider: str,
        message: str,
        presentation: str | None,
        timeout: float | None,
        interaction: str = "manual",
    ) -> None:
        """Report that verification started.

        ``interaction`` is ``automatic`` while a challenge completes by itself
        (nothing is shown, ``presentation`` is None) and ``manual`` when the
        user must act in the shown ``presentation`` (``window`` or ``vnc``).
        ``reason`` repeats ``provider`` for consumers of the original event.
        """
        # Never include connection details or credentials: consumers only
        # need to know that the user must act and where.
        if self.json_mode:
            self._emit(
                {
                    "event": "verification_required",
                    "reason": provider,
                    "provider": provider,
                    "interaction": interaction,
                    "message": message,
                    "presentation": presentation,
                    "timeout": timeout,
                }
            )
        elif interaction == "automatic":
            logging.getLogger("goexport.verification").info(
                "%s Waiting for it to finish.", message
            )
        else:
            waiting = f"Waiting up to {int(timeout)} seconds" if timeout else "Waiting"
            logging.getLogger("goexport.verification").warning(
                "%s %s; press Ctrl+C to cancel.", message, waiting
            )

    def verification_complete(self, provider: str | None = None) -> None:
        if self.json_mode:
            event: dict[str, Any] = {"event": "verification_complete"}
            if provider:
                event["provider"] = provider
            self._emit(event)
        else:
            name = {"anubis": "Anubis", "cloudflare": "Browser"}.get(
                provider or "", "Browser"
            )
            logging.getLogger("goexport.verification").info(
                "%s verification complete; resuming export.", name
            )

    def verification_failed(
        self, message: str, reason: str, provider: str | None = None
    ) -> None:
        # The command's error event follows; normal mode logs the error once.
        if self.json_mode:
            event: dict[str, Any] = {
                "event": "verification_failed",
                "message": message,
                "reason": reason,
            }
            if provider:
                event["provider"] = provider
            self._emit(event)

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
