from __future__ import annotations

import re
from pathlib import Path

from .repository import RepositoryContext


def relevant_files(context: RepositoryContext, request: str, *, limit: int = 12) -> list[Path]:
    tokens = {token.lower() for token in re.findall(r"[A-Za-z0-9_/-]{3,}", request)}
    scored: list[tuple[int, Path]] = []
    for relative in context.tree:
        path = context.root / relative
        score = 0
        lower = relative.lower()
        if path.name.lower() in {"readme.md", "pyproject.toml", "package.json", "cargo.toml", "go.mod"}:
            score += 3
        score += sum(2 for token in tokens if token in lower)
        if path.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go"}:
            score += 1
        if score:
            scored.append((score, path))
    scored.sort(key=lambda item: (-item[0], str(item[1])))
    return [path for _, path in scored[:limit]]