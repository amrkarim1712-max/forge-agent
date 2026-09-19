from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionMemory:
    messages: list[dict[str, Any]] = field(default_factory=list)

    def add(self, message: dict[str, Any]) -> None:
        self.messages.append(message)