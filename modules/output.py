# Structured output module for server environment
# When --no-input is enabled, emit line-delimited JSON to STDOUT

import json
import sys
import time
from typing import Optional, Any

class StructuredOutput:
    """
    Manages structured JSON output for server environments.
    When enabled, emits line-delimited JSON to STDOUT suitable for real-time parsing.
    """
    
    def __init__(self, enabled: bool = False):
        self._enabled = enabled
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
    
    def emit(self, event: str, data: Optional[dict] = None, **kwargs) -> None:
        """
        Emit a structured JSON event to STDOUT.
        
        :param event: Event type (e.g., "started", "progress", "completed", "skipped", "error")
        :param data: Optional dictionary of additional data
        :param kwargs: Additional key-value pairs to include in the output
        """
        if not self._enabled:
            return
        
        output = {
            "event": event,
            "timestamp": time.time(),
        }
        
        if data:
            output.update(data)
        
        if kwargs:
            output.update(kwargs)
        
        # Write to STDOUT as line-delimited JSON
        print(json.dumps(output), file=sys.stdout, flush=True)
    
    def started(self, message: Optional[str] = None, **kwargs) -> None:
        """Emit a 'started' event."""
        data = {}
        if message:
            data["message"] = message
        self.emit("started", data, **kwargs)
    
    def progress(self, message: str, stage: Optional[str] = None, **kwargs) -> None:
        """Emit a 'progress' event."""
        data = {"message": message}
        if stage:
            data["stage"] = stage
        self.emit("progress", data, **kwargs)
    
    def completed(self, output_path: Optional[str] = None, **kwargs) -> None:
        """Emit a 'completed' event."""
        data = {}
        if output_path:
            data["output_path"] = output_path
        self.emit("completed", data, **kwargs)
    
    def skipped(self, reason: str, **kwargs) -> None:
        """Emit a 'skipped' event (e.g., due to timeout)."""
        self.emit("skipped", {"reason": reason}, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Emit an 'error' event."""
        self.emit("error", {"message": message}, **kwargs)


# Global instance - will be configured by main.py
structured_output = StructuredOutput(enabled=False)
