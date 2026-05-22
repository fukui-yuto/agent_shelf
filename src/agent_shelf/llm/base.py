"""Abstract LLM adapter interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Message:
    role: str  # "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"


class LLMAdapter(Protocol):
    def chat(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        system: str | None = None,
    ) -> ChatResponse: ...
