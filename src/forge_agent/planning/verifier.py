from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from forge_agent.tools.tests import detect_test_command


@dataclass
class CheckResult:
    category: str
    command: str
    passed: bool
    output: str
    errors: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    passed: bool
    command: str | None
    output: str
    errors: list[str] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)
    status: str = "not_verified"


class Verifier:
    def __init__(self, root: Path, timeout: int = 120, *, max_output_size: int = 16000) -> None:
        self.root = root
        self.timeout = timeout
        self.max_output_size = max_output_size

    def commands(self) -> list[tuple[str, str]]:
        commands: list[tuple[str, str]] = []
        test = detect_test_command(self.root)
        if test:
            commands.append(("tests", test))
        package = self.root / "package.json"
        if package.is_file():
            try:
                data = json.loads(package.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                manager = "pnpm" if (self.root / "pnpm-lock.yaml").exists() else "yarn" if (self.root / "yarn.lock").exists() else "npm"
                if scripts.get("lint"):
                    commands.append(("lint", f"{manager} run lint"))
                if scripts.get("typecheck"):
                    commands.append(("typecheck", f"{manager} run typecheck"))
                if scripts.get("build"):
                    commands.append(("build", f"{manager} run build"))
            except (OSError, json.JSONDecodeError):
                pass
        if shutil.which("ruff") and (self.root / "ruff.toml").exists():
            commands.append(("lint", "ruff check ."))
        if shutil.which("mypy") and ((self.root / "mypy.ini").exists() or (self.root / "pyproject.toml").exists()):
            commands.append(("typecheck", "mypy ."))
        if shutil.which("eslint") and (self.root / ".eslintrc").exists():
            commands.append(("lint", "eslint ."))
        return commands

    def run(self) -> VerificationResult:
        commands = self.commands()
        if not commands:
            return VerificationResult(True, None, "No supported verification command detected; verification was skipped.", status="not_verified")
        checks: list[CheckResult] = []
        for category, command in commands:
            try:
                result = subprocess.run(
                    command,
                    cwd=self.root,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                output = (result.stdout + "\n" + result.stderr).strip()[-self.max_output_size:]
                checks.append(CheckResult(category, command, result.returncode == 0, output, [] if result.returncode == 0 else [f"Exit code {result.returncode}"]))
            except subprocess.TimeoutExpired:
                checks.append(CheckResult(category, command, False, "", [f"Timed out after {self.timeout}s."]))
        failed = [check for check in checks if not check.passed]
        primary = checks[0]
        output = "\n\n".join(f"[{check.category}] {check.command}\n{check.output}" for check in checks)
        errors = [error for check in failed for error in check.errors]
        return VerificationResult(
            passed=not failed,
            command=primary.command,
            output=output,
            errors=errors,
            checks=checks,
            status="verified" if not failed else "failed",
        )