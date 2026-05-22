"""Agent Router - auto-detect agents from directory structure."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentInfo:
    name: str
    path: Path
    has_knowledge: bool = False
    has_skills: bool = False
    has_prompts: bool = False

    @classmethod
    def from_directory(cls, path: Path) -> AgentInfo:
        name = path.name.replace(" ", "-")
        return cls(
            name=name,
            path=path,
            has_knowledge=(path / "knowledge").is_dir(),
            has_skills=(path / "skills").is_dir(),
            has_prompts=(path / "prompts").is_dir(),
        )


@dataclass
class AgentRouter:
    agents_dir: Path
    _agents: dict[str, AgentInfo] = field(default_factory=dict, init=False)

    def scan(self) -> list[AgentInfo]:
        self._agents.clear()
        if not self.agents_dir.is_dir():
            return []
        for child in sorted(self.agents_dir.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                info = AgentInfo.from_directory(child)
                self._agents[info.name] = info
        return list(self._agents.values())

    def get(self, name: str) -> AgentInfo | None:
        if not self._agents:
            self.scan()
        return self._agents.get(name)

    def list_names(self) -> list[str]:
        if not self._agents:
            self.scan()
        return list(self._agents.keys())
