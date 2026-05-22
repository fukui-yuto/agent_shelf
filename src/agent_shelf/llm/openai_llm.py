"""OpenAI LLM adapter."""

from __future__ import annotations

import json
import os
from typing import Any

import openai

from agent_shelf.llm.base import ChatResponse, Message, ToolCall, ToolDef


class OpenAIAdapter:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._model = model or os.environ.get("LLM_MODEL", "gpt-4o")
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY") or "not-set"
        kwargs: dict[str, Any] = {"api_key": resolved_key}
        url = base_url or os.environ.get("LLM_BASE_URL")
        if url:
            kwargs["base_url"] = url
        self._client = openai.OpenAI(**kwargs)

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        system: str | None = None,
    ) -> ChatResponse:
        oai_messages: list[dict[str, Any]] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        for m in messages:
            oai_messages.append(self._convert_message(m))

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": oai_messages,
        }
        if tools:
            kwargs["tools"] = [self._convert_tool(t) for t in tools]

        response = self._client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    def _convert_message(self, msg: Message) -> dict[str, Any]:
        if msg.role == "tool":
            return {
                "role": "tool",
                "content": msg.content,
                "tool_call_id": msg.tool_call_id or "",
            }
        if msg.tool_calls:
            oai_tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in msg.tool_calls
            ]
            result: dict[str, Any] = {
                "role": "assistant",
                "content": msg.content or None,
                "tool_calls": oai_tool_calls,
            }
            return result
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

    def _parse_response(self, response: Any) -> ChatResponse:
        choice = response.choices[0]
        message = choice.message
        content = message.content or ""
        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )
        stop = "tool_use" if tool_calls else "end_turn"
        return ChatResponse(content=content, tool_calls=tool_calls, stop_reason=stop)
