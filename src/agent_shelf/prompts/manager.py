"""Prompt Manager - build system prompts from prompts/ directory."""

from __future__ import annotations

from pathlib import Path

DEFAULT_SYSTEM_PROMPT = """\
You are a helpful AI assistant specialized in the domain defined by your knowledge base.
Answer questions based on the provided context. If you don't know the answer, say so.
When you use tools, explain what you're doing and why.
"""


class PromptManager:
    def __init__(self, prompts_dir: Path | None) -> None:
        self._prompts_dir = prompts_dir

    def build_system_prompt(self, rag_context: str = "") -> str:
        base = self._load_base_prompt()
        extra = self._load_extra_prompts()
        parts = [base]
        if extra:
            parts.append(extra)
        if rag_context:
            parts.append(
                "## Relevant Knowledge\n\n" + rag_context
            )
        return "\n\n".join(parts)

    def _load_base_prompt(self) -> str:
        if self._prompts_dir is None:
            return DEFAULT_SYSTEM_PROMPT
        system_file = self._prompts_dir / "system.md"
        if system_file.is_file():
            return system_file.read_text(encoding="utf-8").strip()
        return DEFAULT_SYSTEM_PROMPT

    def _load_extra_prompts(self) -> str:
        if self._prompts_dir is None or not self._prompts_dir.is_dir():
            return ""
        parts: list[str] = []
        for f in sorted(self._prompts_dir.glob("*.md")):
            if f.name == "system.md":
                continue
            parts.append(f.read_text(encoding="utf-8").strip())
        return "\n\n".join(parts)
