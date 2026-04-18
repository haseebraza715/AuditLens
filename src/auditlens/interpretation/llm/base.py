from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    @abstractmethod
    def complete_json(self, prompt: str) -> str:
        """Return a JSON string response for the provided prompt."""
