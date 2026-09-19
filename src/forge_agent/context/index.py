"""Lightweight, dependency-free code intelligence for common repositories."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    path: str
    line: int


@dataclass(frozen=True)
class ImportRef:
    module: str
    path: str
    line: int


class CodeIndex:
    def __init__(self, root: Path, files: list[str]) -> None:
        self.root = root
        self.files = files
        self.symbols: list[Symbol] = []
        self.imports: list[ImportRef] = []
        self._build()

    def _build(self) -> None:
        for relative in self.files:
            path = self.root / relative
            if path.suffix == ".py":
                self._python(path, relative)
            elif path.suffix in {".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".c", ".cpp", ".h"}:
                self._generic(path, relative)

    def _python(self, path: Path, relative: str) -> None:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            return
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.symbols.append(Symbol(node.name, "class" if isinstance(node, ast.ClassDef) else "function", relative, node.lineno))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.append(ImportRef(alias.name, relative, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports.append(ImportRef(node.module, relative, node.lineno))

    def _generic(self, path: Path, relative: str) -> None:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return
        patterns = (
            (r"\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", "function"),
            (r"\b(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"\b(?:def|func)\s+([A-Za-z_]\w*)", "function"),
            (r"\b(?:struct|enum|trait)\s+([A-Za-z_]\w*)", "type"),
        )
        for line_number, line in enumerate(text.splitlines(), 1):
            for pattern, kind in patterns:
                match = re.search(pattern, line)
                if match:
                    self.symbols.append(Symbol(match.group(1), kind, relative, line_number))
            for match in re.finditer(r"\b(?:import|require|use)\s*[('\"]?([A-Za-z0-9_./@-]+)", line):
                self.imports.append(ImportRef(match.group(1), relative, line_number))

    def find(self, query: str, limit: int = 50) -> list[dict[str, object]]:
        lowered = query.lower()
        matches = [
            {"name": symbol.name, "kind": symbol.kind, "path": symbol.path, "line": symbol.line}
            for symbol in self.symbols
            if lowered in symbol.name.lower()
        ]
        return matches[:limit]

    def describe(self) -> dict[str, object]:
        return {
            "symbols": len(self.symbols),
            "imports": len(self.imports),
            "files_indexed": len(self.files),
            "top_symbols": [symbol.__dict__ for symbol in self.symbols[:100]],
        }