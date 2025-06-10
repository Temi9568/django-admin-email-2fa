class AdminEmail2FAException(Exception):
    """Base exception for AdminEmail2FA errors."""


class IncorrectAttempt(AdminEmail2FAException):
    """Exception raised when an incorrect token is provided."""


class ExpiredToken(AdminEmail2FAException):
    """Exception raised when a token has expired."""


class ThrottleExceeded(AdminEmail2FAException):
    """Exception raised when the rate limit for generating tokens is exceeded."""


class NoMoreRetries(AdminEmail2FAException):
    """Exception raised when the maximum number of incorrect attempts has been
    reached."""
