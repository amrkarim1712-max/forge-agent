from __future__ import annotations

import re
from enum import StrEnum


class Decision(StrEnum):
    SAFE = "SAFE"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"


class PermissionManager:
    """Conservative command and tool classification, not a sandbox boundary."""

    blocked_patterns = (
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r":\(\)\s*\{",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bsudo\b",
        r"\bchmod\s+(-R\s+)?777\b",
        r">\s*/dev/",
    )
    review_patterns = (
        r"\brm(?:\s|$)",
        r"\bgit\s+(?:reset|checkout|clean|push|commit|add)\b",
        r"\b(?:pip|npm|pnpm|yarn|cargo|go)\s+install\b",
        r"\bmv\s",
        r"\bcp\s",
        r"\bmkdir\s",
        r"\bpython(?:3)?\s+-m\s+venv\b",
        r"\b(?:curl|wget|httpie)\b",
        r"\b(?:docker|podman)\s+(?:run|build|push)\b",
    )

    def classify_command(self, command: str) -> Decision:
        if any(re.search(pattern, command, re.IGNORECASE) for pattern in self.blocked_patterns):
            return Decision.BLOCKED
        if any(re.search(pattern, command, re.IGNORECASE) for pattern in self.review_patterns):
            return Decision.REVIEW
        return Decision.SAFE

    def classify_tool(self, name: str) -> Decision:
        if name in {
            "read_file", "list_directory", "search_files", "search_text", "find_symbol",
            "git_status", "git_diff", "git_log", "git_branch", "git_show",
            "run_tests", "run_linter", "run_formatter", "run_type_checker",
        }:
            return Decision.SAFE
        if name in {
            "write_file", "edit_file", "line_edit", "apply_patch", "delete_file", "move_file",
            "run_command", "run_script", "web_search", "git_add", "git_commit",
        }:
            return Decision.REVIEW
        return Decision.BLOCKED