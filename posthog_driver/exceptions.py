"""
PostHog Driver Exceptions

Custom exception classes for PostHog driver error handling.
"""


class PostHogError(Exception):
    """Base exception for all PostHog driver errors"""
    pass


class AuthenticationError(PostHogError):
    """Raised when authentication fails (invalid API key, unauthorized access)"""
    pass


class ObjectNotFoundError(PostHogError):
    """Raised when a requested resource or object type is not found"""
    pass


class QueryError(PostHogError):
    """Raised when a query execution fails"""
    pass


class ConnectionError(PostHogError):
    """Raised when network connection to PostHog API fails"""
    pass


class RateLimitError(PostHogError):
    """Raised when API rate limit is exceeded"""
    pass


class ValidationError(PostHogError):
    """Raised when input validation fails"""
    pass
