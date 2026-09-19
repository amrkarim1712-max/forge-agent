from __future__ import annotations

from collections.abc import Callable

from forge_agent.permissions import Decision


class ApprovalManager:
    def __init__(self, approve_all: bool = False, input_fn: Callable[[str], str] = input) -> None:
        self.approve_all = approve_all
        self.input_fn = input_fn

    def approve(self, label: str, detail: str) -> bool:
        if self.approve_all:
            return True
        answer = self.input_fn(f"\nApproval required for {label}: {detail}\nAllow? [y/N] ")
        return answer.strip().lower() in {"y", "yes"}

    def allows(self, decision: Decision, label: str, detail: str) -> bool:
        if decision == Decision.SAFE:
            return True
        if decision == Decision.BLOCKED:
            return False
        return self.approve(label, detail)