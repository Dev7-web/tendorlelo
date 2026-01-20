"""
Custom exceptions for the application.
"""

from __future__ import annotations


class AppError(Exception):
    """Base application error."""


class NotFoundError(AppError):
    """Raised when a resource is not found."""


class ValidationError(AppError):
    """Raised when validation fails."""


class ProcessingError(AppError):
    """Raised when processing fails."""
