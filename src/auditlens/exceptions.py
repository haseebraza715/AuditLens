from __future__ import annotations


class AuditLensError(RuntimeError):
    """Base exception for AuditLens."""


class Layer2Error(AuditLensError):
    """Base exception for Layer 2 (interpretation) failures."""


class Layer2ConfigurationError(Layer2Error):
    """Raised when Layer 2 runtime configuration is invalid."""


class Layer2ProviderError(Layer2Error):
    """Raised when the LLM provider request fails."""


class Layer2InvalidResponseError(Layer2Error):
    """Raised when provider output cannot be parsed."""
