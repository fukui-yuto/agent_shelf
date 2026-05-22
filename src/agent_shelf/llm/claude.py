"""Claude (Anthropic) LLM adapter."""

from __future__ import annotations

import os
from typing import Any

import anthropic

from agent_shelf.llm.base import ChatResponse, Message, ToolCall, ToolDef


class ClaudeAdapter:
    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self._model = model or os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
        self._client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        system: str | None = None,
    ) -> ChatResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [self._convert_message(m) for m in messages],
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [self._convert_tool(t) for t in tools]

        response = self._client.messages.create(**kwargs)
        return self._parse_response(response)

    def _convert_message(self, msg: Message) -> dict[str, Any]:
        if msg.role == "tool":
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content,
                    }
                ],
            }
        if msg.tool_calls:
            content: list[dict[str, Any]] = []
            if msg.content:
                content.append({"type": "text", "text": msg.content})
            for tc in msg.tool_calls:
                content.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                )
            return {"role": "assistant", "content": content}
        return {"role": msg.role, "content": msg.content}

    def _convert_tool(self, tool: ToolDef) -> dict[str, Any]:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }

    def _parse_response(self, response: Any) -> ChatResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input)
                )
        return ChatResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
        )
