"""Domain-level exceptions."""


class UserNotFoundError(Exception):
    """Raised when a user is not found."""


class DuplicateEmailError(Exception):
    """Raised when attempting to create a user with an email that already exists."""


class InvalidRoleError(Exception):
    """Raised when an invalid role is specified."""
