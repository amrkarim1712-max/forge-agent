from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class AgentPhase(StrEnum):
    INITIALIZE = "INITIALIZE"
    INSPECT = "INSPECT"
    UNDERSTAND = "UNDERSTAND"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REPAIR = "REPAIR"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass
class AgentState:
    request: str
    cwd: Path
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    plan: Any = None
    relevant_files: list[Path] = field(default_factory=list)
    iteration: int = 0
    errors: list[str] = field(default_factory=list)
    final_response: str | None = None
    changed_files: set[str] = field(default_factory=set)
    phase: AgentPhase = AgentPhase.INITIALIZE
    current_objective: str = ""
    completed_steps: set[int] = field(default_factory=set)
    pending_steps: list[str] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    repair_attempts: int = 0
    provider_name: str = ""
    model_name: str = ""
    context_budget: int = 0
    output_budget: int = 0
    transitions: list[AgentPhase] = field(default_factory=list)

    def transition(self, phase: AgentPhase) -> None:
        self.phase = phase
        self.transitions.append(phase)