from __future__ import annotations


def fit_budget(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[context truncated]..."