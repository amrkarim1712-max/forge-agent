from __future__ import annotations

import os
import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path

from forge_agent.tools.filesystem import IGNORED_DIRS


MARKERS = ("pyproject.toml", "package.json", "Cargo.toml", "go.mod", ".git", "README.md")
SECRET_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "credentials.json"}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


@dataclass
class RepositoryContext:
    root: Path
    tree: list[str]
    ecosystems: list[str]
    recent_changes: list[str]

    @classmethod
    def discover(cls, start: Path) -> "RepositoryContext":
        current = start.resolve()
        for candidate in (current, *current.parents):
            if (candidate / ".git").exists() or any((candidate / marker).exists() for marker in MARKERS):
                current = candidate
                break
        return cls(
            root=current,
            tree=cls._tree(current),
            ecosystems=cls._ecosystems(current),
            recent_changes=cls._recent_changes(current),
        )

    @staticmethod
    def _tree(root: Path, limit: int = 500) -> list[str]:
        entries: list[str] = []
        for current, dirs, files in os.walk(root):
            dirs[:] = sorted(name for name in dirs if name not in IGNORED_DIRS and name != ".git")
            relative = Path(current).relative_to(root)
            for name in sorted(files):
                path = Path(current) / name
                if RepositoryContext._ignored(root, path) or RepositoryContext._secret(path):
                    continue
                try:
                    sample = path.read_bytes()[:2048]
                except OSError:
                    continue
                if b"\x00" in sample:
                    continue
                entries.append(str(relative / name) if str(relative) != "." else name)
                if len(entries) >= limit:
                    return entries
        return entries

    @staticmethod
    def _secret(path: Path) -> bool:
        return path.name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES or path.name.endswith(".secret")

    @staticmethod
    def _ignored(root: Path, path: Path) -> bool:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "check-ignore", "-q", "--", str(path.relative_to(root))],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                return True
        except (OSError, subprocess.TimeoutExpired):
            pass
        gitignore = root / ".gitignore"
        if not gitignore.is_file():
            return False
        relative = str(path.relative_to(root))
        patterns = [line.strip() for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip() and not line.startswith("#")]
        return any(fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern.rstrip("/")) for pattern in patterns if not pattern.startswith("!"))

    @staticmethod
    def _ecosystems(root: Path) -> list[str]:
        checks = {
            "Python": ("pyproject.toml", "requirements.txt", "setup.py"),
            "JavaScript": ("package.json",),
            "TypeScript": ("tsconfig.json",),
            "Rust": ("Cargo.toml",),
            "Go": ("go.mod",),
            "Java": ("pom.xml", "build.gradle"),
            "Ruby": ("Gemfile",),
            "PHP": ("composer.json",),
            "C/C++": ("CMakeLists.txt", "Makefile"),
        }
        return [name for name, markers in checks.items() if any((root / marker).exists() for marker in markers)]

    @staticmethod
    def _recent_changes(root: Path) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "diff", "--name-only", "HEAD~5", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            return [line for line in result.stdout.splitlines() if line][:50]
        except (OSError, subprocess.TimeoutExpired):
            return []