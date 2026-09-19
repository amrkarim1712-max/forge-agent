from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

from forge_agent.core.errors import ToolError
from forge_agent.permissions import Decision
from .registry import ToolRegistry, ToolSpec


def register_test_tool(registry: ToolRegistry, root: Path, timeout: int) -> None:
    def run_tests(command: str | None = None):
        selected = command or detect_test_command(root)
        if not selected:
            return {"passed": False, "failed": False, "command": None, "output": "No supported test command detected.", "errors": ["No tests configured."]}
        try:
            result = subprocess.run(selected, cwd=root, shell=True, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"passed": False, "failed": True, "command": selected, "output": "", "errors": [f"Timed out after {timeout}s."]}
        output = (result.stdout + "\n" + result.stderr).strip()
        return {"passed": result.returncode == 0, "failed": result.returncode != 0, "command": selected, "output": output[-16000:], "errors": [] if result.returncode == 0 else [f"Exit code {result.returncode}"]}

    registry.register(ToolSpec(
        "run_tests", "Run the repository's detected test command or an explicitly supplied bounded command.",
        {"type": "object", "properties": {"command": {"type": "string"}}, "additionalProperties": False},
        run_tests, Decision.SAFE,
    ))

    def quality_check(kind: str, command: str | None = None):
        selected = command or detect_quality_command(root, kind)
        if not selected:
            return {"passed": False, "failed": False, "command": None, "output": f"No {kind} command detected.", "errors": [f"No {kind} tool is configured or installed."]}
        try:
            result = subprocess.run(selected, cwd=root, shell=True, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"passed": False, "failed": True, "command": selected, "output": "", "errors": [f"Timed out after {timeout}s."]}
        output = (result.stdout + "\n" + result.stderr).strip()[-16000:]
        return {"passed": result.returncode == 0, "failed": result.returncode != 0, "command": selected, "output": output, "errors": [] if result.returncode == 0 else [f"Exit code {result.returncode}"]}

    for kind in ("linter", "formatter", "type_checker"):
        registry.register(ToolSpec(
            f"run_{kind}",
            f"Run a detected {kind} or an explicitly supplied bounded command.",
            {"type": "object", "properties": {"command": {"type": "string"}}, "additionalProperties": False},
            lambda command=None, kind=kind: quality_check(kind, command),
            Decision.SAFE,
        ))


def detect_test_command(root: Path) -> str | None:
    has_python_tests = (
        (root / "tests").is_dir()
        or (root / "pytest.ini").exists()
        or (root / "pyproject.toml").exists()
        or any(root.glob("test_*.py"))
        or any(root.glob("*_test.py"))
    )
    if has_python_tests:
        return "python -m pytest"
    if (root / "package.json").exists():
        return "npm test -- --runInBand"
    if (root / "Cargo.toml").exists():
        return "cargo test"
    if (root / "go.mod").exists():
        return "go test ./..."
    return None


def detect_quality_command(root: Path, kind: str) -> str | None:
    package = root / "package.json"
    if package.is_file():
        try:
            import json
            scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
            manager = "pnpm" if (root / "pnpm-lock.yaml").exists() else "yarn" if (root / "yarn.lock").exists() else "npm"
            script_name = {"linter": "lint", "formatter": "format", "type_checker": "typecheck"}[kind]
            if scripts.get(script_name):
                return f"{manager} run {script_name}"
        except (OSError, ValueError):
            pass
    commands = {
        "linter": [("ruff", "ruff check ."), ("eslint", "eslint .")],
        "formatter": [("black", "black --check ."), ("prettier", "prettier --check .")],
        "type_checker": [("mypy", "mypy ."), ("pyright", "pyright"), ("tsc", "tsc --noEmit")],
    }
    for executable, command in commands[kind]:
        if shutil.which(executable):
            return command
    return None