from __future__ import annotations

import subprocess
import time
import os
import shlex
from pathlib import Path

from forge_agent.core.errors import ToolError
from forge_agent.permissions import PermissionManager
from .registry import ToolRegistry, ToolSpec


def _safe_environment() -> dict[str, str]:
    blocked = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    return {key: value for key, value in os.environ.items() if not any(part in key.upper() for part in blocked)}


def register_terminal_tools(registry: ToolRegistry, root: Path, timeout: int, *, max_output_size: int = 16000, dry_run: bool = False) -> None:
    def run_command(command: str, timeout_seconds: int | None = None):
        manager = registry.permissions
        decision = manager.classify_command(command)
        if decision.value == "BLOCKED":
            raise ToolError("Command blocked by the safety policy.")
        if dry_run:
            return {"command": command, "action": "planned", "dry_run": True, "permission": decision.value}
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command, cwd=root, shell=True, capture_output=True, text=True, env=_safe_environment(),
                timeout=min(timeout_seconds or timeout, timeout),
            )
        except subprocess.TimeoutExpired as exc:
            return {"command": command, "stdout": exc.stdout or "", "stderr": f"Timed out after {timeout}s", "exit_code": None, "duration_seconds": round(time.monotonic() - started, 2)}
        return {
            "command": command,
            "stdout": completed.stdout[-max_output_size:],
            "stderr": completed.stderr[-max_output_size:],
            "exit_code": completed.returncode,
            "duration_seconds": round(time.monotonic() - started, 2),
            "permission": decision.value,
        }

    def run_script(script: str, args: list[str] | None = None):
        script_path = (root / script).resolve()
        if script_path != root and root not in script_path.parents:
            raise ToolError("Script is outside the project workspace.")
        if not script_path.is_file():
            raise ToolError(f"Script not found: {script}")
        command = shlex.join([str(script_path), *(args or [])])
        return run_command(command)

    registry.register(ToolSpec(
        "run_command", "Run a bounded shell command in the project workspace. Risky commands require approval.",
        {"type": "object", "properties": {"command": {"type": "string"}, "timeout_seconds": {"type": "integer", "minimum": 1}}, "required": ["command"], "additionalProperties": False},
        run_command, registry.permissions.classify_tool("run_command"),
    ))
    registry.register(ToolSpec(
        "run_script", "Run an existing project script with arguments inside the workspace.",
        {"type": "object", "properties": {"script": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}}, "required": ["script"], "additionalProperties": False},
        run_script, registry.permissions.classify_tool("run_script"),
    ))