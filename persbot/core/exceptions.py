from __future__ import annotations


class PersbotError(Exception):
    """Base exception for all Persbot errors."""


class ProviderNotFoundError(PersbotError):
    """Raised when a specified provider is not found."""
