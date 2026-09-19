from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from forge_agent.core.errors import ToolError
from forge_agent.permissions import Decision
from .registry import ToolRegistry, ToolSpec
from .patching import apply_unified_patch


IGNORED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "dist", "build", ".next", ".cache", ".tox", ".idea",
}


def safe_path(root: Path, raw: str, *, allow_outside: bool = False) -> Path:
    candidate = (root / raw).expanduser().resolve() if not Path(raw).is_absolute() else Path(raw).expanduser().resolve()
    if not allow_outside and candidate != root and root not in candidate.parents:
        raise ToolError(f"Path is outside the project workspace: {raw}")
    return candidate


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root)) or "."


def register_filesystem_tools(
    registry: ToolRegistry,
    root: Path,
    *,
    allow_outside: bool = False,
    max_file_size: int = 1000000,
    max_output_size: int = 16000,
    dry_run: bool = False,
    symbol_index=None,
) -> None:
    def read_file(path: str, max_chars: int = 50000):
        target = safe_path(root, path, allow_outside=allow_outside)
        if not target.is_file():
            raise ToolError(f"File not found: {path}")
        if target.stat().st_size > max_file_size:
            raise ToolError(f"File exceeds the configured size limit ({max_file_size} bytes): {path}")
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ToolError(f"File is not UTF-8 text: {path}") from exc
        content = content[: min(max_chars, max_output_size)]
        return {"path": _relative(root, target), "content": content, "truncated": len(content) >= max_chars, "sha256": _digest(target)}

    def write_file(path: str, content: str, expected_sha256: str | None = None):
        target = safe_path(root, path, allow_outside=allow_outside)
        if len(content.encode("utf-8")) > max_file_size:
            raise ToolError(f"File exceeds the configured size limit ({max_file_size} bytes): {path}")
        if expected_sha256 and target.is_file() and _digest(target) != expected_sha256:
            raise ToolError("The file changed since it was inspected; refusing to overwrite it.")
        if dry_run:
            return {"path": _relative(root, target), "bytes": len(content.encode("utf-8")), "action": "planned", "dry_run": True}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": _relative(root, target), "bytes": target.stat().st_size, "action": "created_or_replaced", "sha256": _digest(target)}

    def edit_file(path: str, old_text: str, new_text: str, expected_sha256: str | None = None):
        target = safe_path(root, path, allow_outside=allow_outside)
        if not target.is_file():
            raise ToolError(f"File not found: {path}")
        if target.stat().st_size > max_file_size:
            raise ToolError(f"File exceeds the configured size limit ({max_file_size} bytes): {path}")
        content = target.read_text(encoding="utf-8")
        if expected_sha256 and _digest(target) != expected_sha256:
            raise ToolError("The file changed since it was inspected; refusing to edit it.")
        count = content.count(old_text)
        if count == 0:
            raise ToolError("The target text was not found; no changes were made.")
        if count > 1:
            raise ToolError(f"The target text is ambiguous ({count} matches); no changes were made.")
        updated = content.replace(old_text, new_text)
        if len(updated.encode("utf-8")) > max_file_size:
            raise ToolError(f"Edited file exceeds the configured size limit ({max_file_size} bytes): {path}")
        if dry_run:
            return {"path": _relative(root, target), "bytes": len(updated.encode("utf-8")), "action": "planned", "dry_run": True}
        target.write_text(updated, encoding="utf-8")
        return {"path": _relative(root, target), "bytes": target.stat().st_size, "action": "edited", "sha256": _digest(target)}

    def line_edit(path: str, start_line: int, end_line: int, content: str):
        target = safe_path(root, path, allow_outside=allow_outside)
        if not target.is_file():
            raise ToolError(f"File not found: {path}")
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        if start_line < 1 or end_line < start_line or end_line > len(lines):
            raise ToolError(f"Invalid line range {start_line}-{end_line} for {path}")
        updated = "".join(lines[: start_line - 1] + [content if content.endswith("\n") else content + "\n"] + lines[end_line:])
        return write_file(path, updated, expected_sha256=_digest(target))

    def delete_file(path: str, expected_sha256: str | None = None):
        target = safe_path(root, path, allow_outside=allow_outside)
        if not target.is_file():
            raise ToolError(f"File not found: {path}")
        if expected_sha256 and _digest(target) != expected_sha256:
            raise ToolError("The file changed since it was inspected; refusing to delete it.")
        if dry_run:
            return {"path": _relative(root, target), "action": "planned", "dry_run": True}
        target.unlink()
        return {"path": _relative(root, target), "action": "deleted"}

    def move_file(source: str, destination: str, expected_sha256: str | None = None):
        source_path = safe_path(root, source, allow_outside=allow_outside)
        destination_path = safe_path(root, destination, allow_outside=allow_outside)
        if not source_path.is_file():
            raise ToolError(f"File not found: {source}")
        if destination_path.exists():
            raise ToolError(f"Destination already exists: {destination}")
        if expected_sha256 and _digest(source_path) != expected_sha256:
            raise ToolError("The source file changed since it was inspected; refusing to move it.")
        if dry_run:
            return {"source": _relative(root, source_path), "destination": _relative(root, destination_path), "action": "planned", "dry_run": True}
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.rename(destination_path)
        return {"source": _relative(root, source_path), "destination": _relative(root, destination_path), "action": "moved"}

    def list_directory(path: str = "."):
        target = safe_path(root, path, allow_outside=allow_outside)
        if not target.is_dir():
            raise ToolError(f"Directory not found: {path}")
        entries = []
        for entry in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            if entry.is_dir() and entry.name in IGNORED_DIRS:
                continue
            entries.append({"name": entry.name, "type": "directory" if entry.is_dir() else "file"})
        return {"path": _relative(root, target), "entries": entries}

    def search_files(query: str, path: str = ".", max_results: int = 50):
        base = safe_path(root, path, allow_outside=allow_outside)
        matches: list[dict[str, object]] = []
        for current, dirs, files in os.walk(base):
            dirs[:] = [name for name in dirs if name not in IGNORED_DIRS]
            for name in files:
                target = Path(current) / name
                try:
                    text = target.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                for index, line in enumerate(text.splitlines(), start=1):
                    if query.lower() in line.lower():
                        matches.append({"path": _relative(root, target), "line": index, "text": line[:max_output_size]})
                        if len(matches) >= max_results:
                            return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}

    def find_symbol(query: str, max_results: int = 50):
        if symbol_index is None:
            return {"matches": [], "error": "Code index is unavailable."}
        return {"matches": symbol_index.find(query, max_results)}

    def apply_patch(patch: str):
        return apply_unified_patch(root, patch, max_file_size=max_file_size, dry_run=dry_run)

    string_properties = {"path": {"type": "string"}, "expected_sha256": {"type": "string"}}
    registry.register(ToolSpec("read_file", "Read a bounded UTF-8 text file and return its SHA-256 digest.", {"type": "object", "properties": {"path": {"type": "string"}, "max_chars": {"type": "integer", "minimum": 1}}, "required": ["path"], "additionalProperties": False}, read_file, Decision.SAFE))
    registry.register(ToolSpec("write_file", "Create or replace a project file. Requires approval unless auto-approved.", {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "expected_sha256": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}, write_file, Decision.REVIEW))
    registry.register(ToolSpec("edit_file", "Replace one unambiguous text occurrence in a project file.", {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}, "expected_sha256": {"type": "string"}}, "required": ["path", "old_text", "new_text"], "additionalProperties": False}, edit_file, Decision.REVIEW))
    registry.register(ToolSpec("line_edit", "Replace an inclusive line range in a project file.", {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer", "minimum": 1}, "end_line": {"type": "integer", "minimum": 1}, "content": {"type": "string"}}, "required": ["path", "start_line", "end_line", "content"], "additionalProperties": False}, line_edit, Decision.REVIEW))
    registry.register(ToolSpec("delete_file", "Delete one project file after explicit approval.", {"type": "object", "properties": string_properties, "required": ["path"], "additionalProperties": False}, delete_file, Decision.REVIEW))
    registry.register(ToolSpec("move_file", "Move one project file after explicit approval.", {"type": "object", "properties": {"source": {"type": "string"}, "destination": {"type": "string"}, "expected_sha256": {"type": "string"}}, "required": ["source", "destination"], "additionalProperties": False}, move_file, Decision.REVIEW))
    registry.register(ToolSpec("list_directory", "List a project directory while omitting generated directories.", {"type": "object", "properties": {"path": {"type": "string"}}, "additionalProperties": False}, list_directory, Decision.SAFE))
    registry.register(ToolSpec("search_files", "Search text files in the project for a case-insensitive string.", {"type": "object", "properties": {"query": {"type": "string"}, "path": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"], "additionalProperties": False}, search_files, Decision.SAFE))
    registry.register(ToolSpec("search_text", "Alias for search_files for natural-language tool callers.", {"type": "object", "properties": {"query": {"type": "string"}, "path": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"], "additionalProperties": False}, search_files, Decision.SAFE))
    registry.register(ToolSpec("find_symbol", "Find functions, classes, and types in the repository code index.", {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"], "additionalProperties": False}, find_symbol, Decision.SAFE))
    registry.register(ToolSpec("apply_patch", "Apply a validated unified diff to project files.", {"type": "object", "properties": {"patch": {"type": "string"}}, "required": ["patch"], "additionalProperties": False}, apply_patch, Decision.REVIEW))