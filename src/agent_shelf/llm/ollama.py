"""Ollama LLM adapter."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import httpx

from agent_shelf.llm.base import ChatResponse, Message, ToolCall, ToolDef


class OllamaAdapter:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._model = model or os.environ.get("LLM_MODEL", "llama3.1:8b")
        self._base_url = (
            base_url or os.environ.get("LLM_BASE_URL", "http://localhost:11434")
        ).rstrip("/")

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        system: str | None = None,
    ) -> ChatResponse:
        ollama_messages: list[dict[str, Any]] = []
        if system:
            ollama_messages.append({"role": "system", "content": system})
        for m in messages:
            ollama_messages.append(self._convert_message(m))

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = [self._convert_tool(t) for t in tools]

        resp = httpx.post(
            f"{self._base_url}/api/chat",
            json=payload,
            timeout=120.0,
        )
        resp.raise_for_status()
        return self._parse_response(resp.json())

    def _convert_message(self, msg: Message) -> dict[str, Any]:
        if msg.role == "tool":
            return {"role": "tool", "content": msg.content}
        return {"role": msg.role, "content": msg.content}

    def _convert_tool(self, tool: ToolDef) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    def _parse_response(self, data: dict[str, Any]) -> ChatResponse:
        message = data.get("message", {})
        content = message.get("content", "")
        tool_calls: list[ToolCall] = []
        for tc in message.get("tool_calls", []):
            func = tc.get("function", {})
            args = func.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            tool_calls.append(
                ToolCall(
                    id=uuid.uuid4().hex[:12],
                    name=func.get("name", ""),
                    arguments=args,
                )
            )
        return ChatResponse(content=content, tool_calls=tool_calls)
