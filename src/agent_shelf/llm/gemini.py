"""Google Gemini LLM adapter."""

from __future__ import annotations

import os
import uuid
from typing import Any

import httpx

from agent_shelf.llm.base import ChatResponse, Message, ToolCall, ToolDef

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiAdapter:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model = model or os.environ.get("LLM_MODEL", "gemini-2.5-flash")
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        system: str | None = None,
    ) -> ChatResponse:
        contents = self._build_contents(messages)
        payload: dict[str, Any] = {"contents": contents}

        if system:
            payload["system_instruction"] = {
                "parts": [{"text": system}]
            }

        if tools:
            payload["tools"] = [
                {
                    "function_declarations": [
                        self._convert_tool(t) for t in tools
                    ]
                }
            ]

        url = (
            f"{GEMINI_API_BASE}/models/{self._model}:generateContent"
            f"?key={self._api_key}"
        )
        resp = httpx.post(url, json=payload, timeout=120.0)
        resp.raise_for_status()
        return self._parse_response(resp.json())

    def _build_contents(self, messages: list[Message]) -> list[dict[str, Any]]:
        contents: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "tool":
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "name": msg.tool_call_id or "unknown",
                                    "response": {"result": msg.content},
                                }
                            }
                        ],
                    }
                )
            elif msg.tool_calls:
                parts: list[dict[str, Any]] = []
                if msg.content:
                    parts.append({"text": msg.content})
                for tc in msg.tool_calls:
                    parts.append(
                        {
                            "function_call": {
                                "name": tc.name,
                                "args": tc.arguments,
                            }
                        }
                    )
                contents.append({"role": "model", "parts": parts})
            else:
                role = "model" if msg.role == "assistant" else "user"
                contents.append(
                    {"role": role, "parts": [{"text": msg.content}]}
                )
        return contents

    def _convert_tool(self, tool: ToolDef) -> dict[str, Any]:
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }

    def _parse_response(self, data: dict[str, Any]) -> ChatResponse:
        candidates = data.get("candidates", [])
        if not candidates:
            return ChatResponse(content="", tool_calls=[])

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(
                    ToolCall(
                        id=uuid.uuid4().hex[:12],
                        name=fc["name"],
                        arguments=fc.get("args", {}),
                    )
                )

        return ChatResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
        )
