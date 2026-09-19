from __future__ import annotations

from pathlib import Path

from forge_agent.core.errors import ToolError


def _safe_path(root: Path, raw: str) -> Path:
    candidate = (root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
    if candidate != root and root not in candidate.parents:
        raise ToolError(f"Path is outside the project workspace: {raw}")
    return candidate


def apply_unified_patch(
    root: Path,
    patch_text: str,
    *,
    max_file_size: int = 1000000,
    dry_run: bool = False,
) -> dict[str, object]:
    """Apply a small standard unified diff without shelling out to patch(1)."""
    lines = patch_text.splitlines(keepends=True)
    changes: list[tuple[str, str, list[tuple[int, list[str], list[str]]]]] = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith("--- "):
            index += 1
            continue
        old_name = lines[index][4:].strip().split("\t", 1)[0]
        index += 1
        if index >= len(lines) or not lines[index].startswith("+++ "):
            raise ToolError("Malformed patch: every old file header needs a new file header.")
        new_name = lines[index][4:].strip().split("\t", 1)[0]
        index += 1
        hunks: list[tuple[int, list[str], list[str]]] = []
        while index < len(lines) and not lines[index].startswith("--- "):
            if not lines[index].startswith("@@"):
                index += 1
                continue
            header = lines[index]
            try:
                old_start = int(header.split(" ")[1].split(",")[0].lstrip("-"))
            except (IndexError, ValueError) as exc:
                raise ToolError(f"Malformed patch hunk header: {header.strip()}") from exc
            index += 1
            expected: list[str] = []
            replacement: list[str] = []
            while index < len(lines) and not lines[index].startswith(("@@", "--- ")):
                line = lines[index]
                if line.startswith("\\ No newline"):
                    index += 1
                    continue
                if not line or line[0] not in " +-":
                    raise ToolError("Malformed patch: hunk lines must begin with space, +, or -.")
                if line[0] in " -":
                    expected.append(line[1:])
                if line[0] in " +":
                    replacement.append(line[1:])
                index += 1
            hunks.append((old_start, expected, replacement))
        changes.append((old_name, new_name, hunks))

    if not changes:
        raise ToolError("No unified diff file sections were found.")

    results: list[dict[str, object]] = []
    for old_name, new_name, hunks in changes:
        source_name = old_name.removeprefix("a/")
        destination_name = new_name.removeprefix("b/")
        source = None if source_name == "/dev/null" else _safe_path(root, source_name)
        destination = None if destination_name == "/dev/null" else _safe_path(root, destination_name)
        original = [] if source is None else source.read_text(encoding="utf-8").splitlines(keepends=True)
        updated = list(original)
        offset = 0
        for old_start, expected, replacement in hunks:
            position = max(0, old_start - 1 + offset)
            if updated[position : position + len(expected)] != expected:
                nearby = "\n".join(updated[max(0, position - 2) : position + len(expected) + 2])
                raise ToolError(f"Patch context did not match {source_name}. Nearby content:\n{nearby[:1000]}")
            updated[position : position + len(expected)] = replacement
            offset += len(replacement) - len(expected)
        content = "".join(updated)
        if destination is not None and len(content.encode("utf-8")) > max_file_size:
            raise ToolError(f"Patched file exceeds the configured size limit: {destination_name}")
        if not dry_run:
            if destination is None:
                if source and source.exists():
                    source.unlink()
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8")
        results.append({
            "source": source_name,
            "destination": destination_name,
            "action": "planned" if dry_run else "patched",
            "dry_run": dry_run,
        })
    return {"files": results, "dry_run": dry_run}