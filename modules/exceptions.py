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
