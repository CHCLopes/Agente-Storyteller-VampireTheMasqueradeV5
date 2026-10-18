"""Concrete transports kept behind the product-owned LLM contract."""

from .gemini import GeminiAdapter
from .groq import GroqAdapter
from .nvidia import NvidiaNimAdapter
from .openai_compatible import OpenAICompatibleAdapter
from .openrouter import OpenRouterAdapter

__all__ = [
    "GeminiAdapter",
    "GroqAdapter",
    "NvidiaNimAdapter",
    "OpenAICompatibleAdapter",
    "OpenRouterAdapter",
]
