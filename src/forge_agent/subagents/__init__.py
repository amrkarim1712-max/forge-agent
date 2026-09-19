"""Optional bounded role definitions for future orchestrated sub-agents."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    RESEARCHER = "researcher"
    PLANNER = "planner"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"


@dataclass(frozen=True)
class SubAgentBudget:
    max_iterations: int = 8
    max_output_tokens: int = 2000
    timeout_seconds: int = 120


@dataclass(frozen=True)
class SubAgentTask:
    role: Role
    objective: str
    budget: SubAgentBudget = SubAgentBudget()