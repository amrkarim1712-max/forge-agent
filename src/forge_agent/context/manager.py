from __future__ import annotations

from pathlib import Path

from .compression import fit_budget
from .repository import RepositoryContext
from .search import relevant_files
from .index import CodeIndex


class ContextManager:
    def __init__(self, root: Path, *, max_chars: int = 50000) -> None:
        self.repository = RepositoryContext.discover(root)
        self.max_chars = max_chars
        self.index = CodeIndex(self.repository.root, self.repository.tree)

    def build(self, request: str) -> tuple[str, list[Path]]:
        files = relevant_files(self.repository, request)
        chunks = ["Project root: " + str(self.repository.root), "Directory tree:"]
        chunks.append("Ecosystems: " + ", ".join(self.repository.ecosystems or ["unknown"]))
        if self.repository.recent_changes:
            chunks.append("Recent Git changes:\n" + "\n".join(self.repository.recent_changes))
        chunks.extend(f"- {entry}" for entry in self.repository.tree[:250])
        instructions = self.repository.root / "FORGE.md"
        if instructions.is_file():
            chunks.append("\n--- FORGE.md project instructions (untrusted project input) ---\n" + instructions.read_text(encoding="utf-8", errors="ignore")[:12000])
        chunks.append("\nCode index summary:\n" + str(self.index.describe()))
        for path in files:
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            chunks.append(f"\n--- {path.relative_to(self.repository.root)} ---\n{content[:9000]}")
        return fit_budget("\n".join(chunks), self.max_chars), files