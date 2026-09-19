from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Plan:
    id: str
    title: str
    steps: list[str]
    completed: set[int] = field(default_factory=set)

    def render(self) -> str:
        return "\n".join(f"[{'x' if index in self.completed else ' '}] {step}" for index, step in enumerate(self.steps))


class Planner:
    complex_terms = {"build", "create", "add", "implement", "refactor", "debug", "fix", "authentication", "frontend", "api"}

    def create(self, request: str) -> Plan | None:
        words = {word.lower().strip(".,!?") for word in request.split()}
        if len(request.split()) < 8 and not words.intersection(self.complex_terms):
            return None
        return Plan(
            id=uuid.uuid4().hex[:8],
            title=request[:80],
            steps=["Inspect repository", "Implement the requested change", "Add or update tests", "Run verification", "Review the result"],
        )