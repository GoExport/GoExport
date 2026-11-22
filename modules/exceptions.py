# Custom exceptions for GoExport

class GoExportError(Exception):
    """Base exception class for GoExport."""
    pass


class TimeoutError(GoExportError):
    """Raised when an operation times out."""
    
    def __init__(self, message: str, timeout_type: str = "unknown"):
        """
        Initialize the TimeoutError.
        
        :param message: Human-readable description of the timeout
        :param timeout_type: Type of timeout ('load' or 'video')
        """
        super().__init__(message)
        self.message = message
        self.timeout_type = timeout_type


class BrowserClosedError(GoExportError):
    """Raised when Chromium is closed before an export completes."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BotProtectionError(GoExportError):
    """Raised when a website's anti-bot protection blocks the export.

    ``protection`` is ``"cloudflare"`` when a Cloudflare challenge was shown
    (which GoExport refuses to bypass), or ``"anubis"`` when the Anubis check
    did not finish in time.
    """

    def __init__(self, message: str, protection: str = "unknown"):
        super().__init__(message)
        self.message = message
        self.protection = protection
