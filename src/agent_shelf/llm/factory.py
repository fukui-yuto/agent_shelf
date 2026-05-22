"""LLM adapter factory."""

from __future__ import annotations

import os

from agent_shelf.llm.base import LLMAdapter


def create_llm_adapter(provider: str | None = None) -> LLMAdapter:
    provider = (provider or os.environ.get("LLM_PROVIDER", "claude")).lower()

    if provider == "claude":
        from agent_shelf.llm.claude import ClaudeAdapter
        return ClaudeAdapter()
    elif provider == "openai":
        from agent_shelf.llm.openai_llm import OpenAIAdapter
        return OpenAIAdapter()
    elif provider == "gemini":
        from agent_shelf.llm.gemini import GeminiAdapter
        return GeminiAdapter()
    elif provider == "ollama":
        from agent_shelf.llm.ollama import OllamaAdapter
        return OllamaAdapter()
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Supported: claude, openai, gemini, ollama"
        )
