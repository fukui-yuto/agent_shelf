"""Agent Runtime - orchestrates RAG, skills, prompts, and LLM."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_shelf.embeddings import create_embedding_adapter
from agent_shelf.llm import ChatResponse, Message, create_llm_adapter
from agent_shelf.prompts.manager import PromptManager
from agent_shelf.rag.engine import RAGEngine
from agent_shelf.router import AgentInfo
from agent_shelf.skills.executor import SkillExecutor


class AgentRuntime:
    def __init__(self, agent_info: AgentInfo) -> None:
        self._info = agent_info
        self._history: list[Message] = []

        # Initialize components
        self._llm = create_llm_adapter()

        prompts_dir = agent_info.path / "prompts" if agent_info.has_prompts else None
        self._prompt_manager = PromptManager(prompts_dir)

        skills_dir = agent_info.path / "skills" if agent_info.has_skills else None
        self._skill_executor = SkillExecutor(skills_dir)

        # RAG engine (lazy init)
        self._rag: RAGEngine | None = None
        if agent_info.has_knowledge:
            embedding = create_embedding_adapter()
            self._rag = RAGEngine(
                agent_name=agent_info.name,
                knowledge_dir=agent_info.path / "knowledge",
                embedding_adapter=embedding,
            )

    def index_knowledge(self) -> int:
        if self._rag is None:
            return 0
        return self._rag.index()

    def chat(self, user_input: str) -> dict[str, Any]:
        # RAG retrieval
        rag_context = ""
        sources: list[dict[str, str]] = []
        if self._rag and self._rag.has_index():
            hits = self._rag.query(user_input)
            if hits:
                sources = hits
                rag_context = "\n\n---\n\n".join(
                    f"[Source: {h['source']}]\n{h['text']}" for h in hits
                )

        # Build system prompt
        system_prompt = self._prompt_manager.build_system_prompt(rag_context)

        # Add user message
        self._history.append(Message(role="user", content=user_input))

        # Get tool definitions
        tools = self._skill_executor.get_tool_defs() or None

        # LLM call loop (handle tool calls)
        executed_tools: list[dict[str, Any]] = []
        response = self._llm.chat(
            messages=self._history,
            tools=tools,
            system=system_prompt,
        )

        # Tool call loop
        while response.tool_calls:
            # Record assistant message with tool calls
            self._history.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            # Execute each tool call
            for tc in response.tool_calls:
                result = self._skill_executor.execute(tc.name, tc.arguments)
                executed_tools.append(
                    {"skill": tc.name, "arguments": tc.arguments, "result": result}
                )
                self._history.append(
                    Message(role="tool", content=result, tool_call_id=tc.id)
                )

            # Call LLM again with tool results
            response = self._llm.chat(
                messages=self._history,
                tools=tools,
                system=system_prompt,
            )

        # Record final assistant message
        self._history.append(Message(role="assistant", content=response.content))

        return {
            "reply": response.content,
            "sources": sources,
            "tool_calls": executed_tools,
        }
