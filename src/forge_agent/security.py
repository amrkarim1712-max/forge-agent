"""Small, conservative protections for untrusted tool and provider data."""

from __future__ import annotations

import os
import re
from typing import Any


_SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "PRIVATE")
_ASSIGNMENT_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|private[_-]?key)\b(\s*[:=]\s*)([^\s,;&]+)"
)


def _known_secrets() -> list[str]:
    values = []
    for name, value in os.environ.items():
        if any(marker in name.upper() for marker in _SECRET_ENV_MARKERS) and len(value) >= 8:
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


def redact_text(value: str) -> str:
    redacted = value
    for secret in _known_secrets():
        redacted = redacted.replace(secret, "[REDACTED]")
    return _ASSIGNMENT_SECRET.sub(r"\1\2[REDACTED]", redacted)


def redact_data(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(key): redact_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_data(item) for item in value)
    return value