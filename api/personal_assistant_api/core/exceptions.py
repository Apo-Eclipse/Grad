"""Custom exceptions for the application."""


class DatabaseError(Exception):
    """Raised when a database operation fails."""
    pass


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


class NotFoundError(Exception):
    """Raised when a requested resource is not found."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass
