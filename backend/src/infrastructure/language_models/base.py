"""Base LLM model ABC."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class BaseLLMModel(ABC):
    @abstractmethod
    async def invoke(self, messages: list[dict], **kwargs) -> dict:
        """Invoke the model and return the full response."""
        ...

    @abstractmethod
    async def prompt(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        """Stream the model response as text chunks."""
        ...
