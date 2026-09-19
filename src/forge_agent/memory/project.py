from __future__ import annotations

from pathlib import Path


class ProjectMemory:
    def __init__(self, root: Path) -> None:
        self.path = root / ".forge" / "project.md"

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.is_file() else ""

    def write(self, content: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content.strip() + "\n", encoding="utf-8")