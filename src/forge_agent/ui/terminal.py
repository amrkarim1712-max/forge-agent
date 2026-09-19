from __future__ import annotations

import sys
from pathlib import Path


class TerminalUI:
    def header(self, model: str, project: Path) -> None:
        print("╭──────────────────────────────────────╮")
        print("│              FORGE AGENT              │")
        print("│                                      │")
        print(f"│  Model: {model:<29}│")
        print(f"│  Project: {str(project)[:25]:<25}│")
        print("╰──────────────────────────────────────╯")

    def status(self, message: str) -> None:
        print(message)

    def response(self, message: str) -> None:
        print(f"\nForge > {message}")

    def error(self, message: str) -> None:
        print(f"Forge error: {message}", file=sys.stderr)

    def prompt(self) -> str:
        return input("\nYou > ").strip()