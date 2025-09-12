class BhyveError(Exception):
    """Base exception for all Bhyve-related errors."""

    pass


class BhyveConnectionError(BhyveError):
    """Raised when there's a connection issue with the Bhyve device or API."""

    pass


class BhyveAuthenticationError(BhyveError):
    """Raised when authentication fails with the Bhyve API."""

    pass


class BhyveDeviceError(BhyveError):
    """Raised when there's an error with a specific Bhyve device."""

    pass


class BhyveAPIError(BhyveError):
    """Raised when there's an error with the Bhyve API response."""

    pass
