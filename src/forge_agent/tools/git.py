from __future__ import annotations

import subprocess
import shlex
from pathlib import Path

from forge_agent.core.errors import ToolError
from forge_agent.permissions import Decision
from .registry import ToolRegistry, ToolSpec


def register_git_tools(registry: ToolRegistry, root: Path, *, dry_run: bool = False, max_output_size: int = 16000) -> None:
    def git(arguments: list[str], *, allow_write: bool = False):
        if dry_run and allow_write:
            return {"command": "git " + shlex.join(arguments), "action": "planned", "dry_run": True}
        try:
            result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ToolError(f"Git command failed: {exc}") from exc
        return {"command": "git " + shlex.join(arguments), "stdout": result.stdout[-max_output_size:], "stderr": result.stderr[-max_output_size:], "exit_code": result.returncode}

    schema = {"type": "object", "properties": {}, "additionalProperties": False}
    for name, command, description in (
        ("git_status", ["status", "--short"], "Show the current Git status."),
        ("git_diff", ["diff"], "Show unstaged Git changes."),
        ("git_log", ["log", "-8", "--oneline"], "Show recent Git commits."),
        ("git_branch", ["branch", "--list"], "Show local Git branches."),
    ):
        registry.register(ToolSpec(name, description, schema, lambda command=command: git(command), Decision.SAFE))
    registry.register(ToolSpec(
        "git_show", "Show a specific Git object or the latest commit.",
        {"type": "object", "properties": {"revision": {"type": "string"}}, "additionalProperties": False},
        lambda revision="HEAD": git(["show", revision]), Decision.SAFE,
    ))
    registry.register(ToolSpec(
        "git_add", "Stage selected paths after explicit approval.",
        {"type": "object", "properties": {"paths": {"type": "array", "items": {"type": "string"}}}, "required": ["paths"], "additionalProperties": False},
        lambda paths: git(["add", "--", *paths], allow_write=True), Decision.REVIEW,
    ))
    registry.register(ToolSpec(
        "git_commit", "Create a local commit after explicit approval. Never pushes.",
        {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"], "additionalProperties": False},
        lambda message: git(["commit", "-m", message], allow_write=True), Decision.REVIEW,
    ))