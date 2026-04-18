from __future__ import annotations


class Layer2Error(RuntimeError):
    """Base Layer 2 exception."""


class Layer2ConfigurationError(Layer2Error):
    """Raised when Layer 2 provider configuration is invalid."""


class Layer2ProviderError(Layer2Error):
    """Raised when the provider request fails."""


class Layer2InvalidResponseError(Layer2Error):
    """Raised when provider output cannot be parsed."""
