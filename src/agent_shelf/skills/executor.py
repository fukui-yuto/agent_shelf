"""Skill executor - load and run Python skills from skills/ directory."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_shelf.llm.base import ToolDef


@dataclass
class SkillMeta:
    name: str
    description: str
    parameters: dict[str, Any]
    file_path: Path


class SkillExecutor:
    def __init__(self, skills_dir: Path | None) -> None:
        self._skills_dir = skills_dir
        self._skills: dict[str, SkillMeta] = {}
        if skills_dir and skills_dir.is_dir():
            self._load_skills()

    def _load_skills(self) -> None:
        assert self._skills_dir is not None
        for py_file in self._skills_dir.glob("*.py"):
            meta = self._parse_skill_meta(py_file)
            if meta:
                self._skills[meta.name] = meta

    def _parse_skill_meta(self, file_path: Path) -> SkillMeta | None:
        content = file_path.read_text(encoding="utf-8")
        pattern = r"#\s*---\s*\n(.*?)#\s*---"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return None

        block = match.group(1)
        description = ""
        parameters: dict[str, Any] = {"type": "object", "properties": {}}
        required: list[str] = []

        for line in block.strip().splitlines():
            line = line.lstrip("#").strip()
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip()
            elif ":" in line and not line.startswith("parameters"):
                # Parse parameter: "  vm_name: string - VMの名前"
                parts = line.split(":", 1)
                param_name = parts[0].strip()
                rest = parts[1].strip()
                type_and_desc = rest.split(" - ", 1)
                param_type = type_and_desc[0].strip()
                param_desc = type_and_desc[1].strip() if len(type_and_desc) > 1 else ""

                json_type = {"string": "string", "int": "integer", "float": "number", "bool": "boolean"}.get(
                    param_type, "string"
                )
                parameters["properties"][param_name] = {
                    "type": json_type,
                    "description": param_desc,
                }
                required.append(param_name)

        if required:
            parameters["required"] = required

        return SkillMeta(
            name=file_path.stem,
            description=description,
            parameters=parameters,
            file_path=file_path,
        )

    def get_tool_defs(self) -> list[ToolDef]:
        return [
            ToolDef(
                name=s.name,
                description=s.description,
                parameters=s.parameters,
            )
            for s in self._skills.values()
        ]

    def execute(self, skill_name: str, arguments: dict[str, Any]) -> str:
        meta = self._skills.get(skill_name)
        if not meta:
            return json.dumps({"error": f"Unknown skill: {skill_name}"})

        try:
            spec = importlib.util.spec_from_file_location(skill_name, meta.file_path)
            if spec is None or spec.loader is None:
                return json.dumps({"error": f"Cannot load skill: {skill_name}"})

            module = importlib.util.module_from_spec(spec)
            sys.modules[skill_name] = module
            spec.loader.exec_module(module)

            run_fn = getattr(module, "run", None)
            if run_fn is None:
                return json.dumps({"error": f"Skill {skill_name} has no run() function"})

            result = run_fn(**arguments)
            return json.dumps(result, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})
        finally:
            sys.modules.pop(skill_name, None)

    def list_skills(self) -> list[SkillMeta]:
        return list(self._skills.values())
