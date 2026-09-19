"""Configuration loading with CLI > environment > user config > defaults precedence."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULTS = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_base_url": "https://api.openai.com/v1",
    "temperature": 0.2,
    "max_tokens": 4096,
    "max_iterations": 30,
    "max_repair_attempts": 5,
    "retry_attempts": 3,
    "retry_backoff": 1.0,
    "command_timeout": 120,
    "tool_timeout": 120,
    "context_budget": 50000,
    "max_output_size": 16000,
    "max_file_size": 1000000,
    "max_parallel_operations": 4,
    "web_search_url": "",
}

PROVIDER_DEFAULTS = {
    "groq": {
        "api_base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
}


def user_config_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "forge" / "config.toml"


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    api_base_url: str
    temperature: float
    max_tokens: int
    max_iterations: int
    max_repair_attempts: int
    retry_attempts: int
    retry_backoff: float
    command_timeout: int
    tool_timeout: int
    context_budget: int
    max_output_size: int
    max_file_size: int
    max_parallel_operations: int
    web_search_url: str
    cwd: Path
    debug: bool = False
    approve_all: bool = False
    dry_run: bool = False

    @property
    def api_key_env(self) -> str | None:
        return {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "compatible": "FORGE_API_KEY",
        }.get(self.provider)

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) if self.api_key_env else None

    def public_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "api_base_url": self.api_base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_iterations": self.max_iterations,
            "max_repair_attempts": self.max_repair_attempts,
            "retry_attempts": self.retry_attempts,
            "retry_backoff": self.retry_backoff,
            "command_timeout": self.command_timeout,
            "tool_timeout": self.tool_timeout,
            "context_budget": self.context_budget,
            "max_output_size": self.max_output_size,
            "max_file_size": self.max_file_size,
            "max_parallel_operations": self.max_parallel_operations,
            "web_search_url": self.web_search_url or "disabled",
            "cwd": str(self.cwd),
            "credential_source_configured": bool(self.api_key_env),
            "api_key_present": bool(self.api_key),
            "dry_run": self.dry_run,
        }


def _read_user_config() -> dict[str, Any]:
    path = user_config_path()
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        return data.get("forge", data)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _env_config() -> dict[str, Any]:
    values: dict[str, Any] = {}
    mapping = {
        "FORGE_PROVIDER": "provider",
        "FORGE_MODEL": "model",
        "FORGE_API_BASE_URL": "api_base_url",
        "MAX_AGENT_ITERATIONS": "max_iterations",
        "MAX_REPAIR_ATTEMPTS": "max_repair_attempts",
        "FORGE_RETRY_ATTEMPTS": "retry_attempts",
        "FORGE_RETRY_BACKOFF": "retry_backoff",
        "FORGE_COMMAND_TIMEOUT": "command_timeout",
        "FORGE_TOOL_TIMEOUT": "tool_timeout",
        "FORGE_CONTEXT_BUDGET": "context_budget",
        "FORGE_MAX_OUTPUT_SIZE": "max_output_size",
        "FORGE_MAX_FILE_SIZE": "max_file_size",
        "FORGE_MAX_PARALLEL_OPERATIONS": "max_parallel_operations",
        "FORGE_WEB_SEARCH_URL": "web_search_url",
    }
    for env_name, key in mapping.items():
        if os.environ.get(env_name):
            values[key] = os.environ[env_name]
    if os.environ.get("FORGE_TEMPERATURE"):
        values["temperature"] = os.environ["FORGE_TEMPERATURE"]
    if os.environ.get("FORGE_MAX_TOKENS"):
        values["max_tokens"] = os.environ["FORGE_MAX_TOKENS"]
    return values


def _coerce(values: dict[str, Any]) -> dict[str, Any]:
    result = dict(values)
    for key in ("temperature", "retry_backoff"):
        if key in result:
            result[key] = float(result[key])
    for key in (
        "max_tokens",
        "max_iterations",
        "max_repair_attempts",
        "retry_attempts",
        "command_timeout",
        "tool_timeout",
        "context_budget",
        "max_output_size",
        "max_file_size",
        "max_parallel_operations",
    ):
        if key in result:
            result[key] = int(result[key])
    return result


def load_settings(
    *,
    cwd: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
    debug: bool = False,
    approve_all: bool = False,
    dry_run: bool = False,
) -> Settings:
    values = dict(DEFAULTS)
    values.update(_read_user_config())
    values.update(_env_config())
    values.update({key: value for key, value in (overrides or {}).items() if value is not None})
    provider_defaults = PROVIDER_DEFAULTS.get(str(values.get("provider")), {})
    for key, value in provider_defaults.items():
        if values.get(key) == DEFAULTS.get(key):
            values[key] = value
    values = _coerce(values)
    project_dir = Path(cwd or os.getcwd()).expanduser().resolve()
    return Settings(cwd=project_dir, debug=debug, approve_all=approve_all, dry_run=dry_run, **values)


def save_user_config(values: dict[str, Any]) -> Path:
    path = user_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[forge]"]
    for key, value in values.items():
        if key not in DEFAULTS or key == "api_key":
            continue
        if isinstance(value, str):
            lines.append(f'{key} = "{value.replace(chr(34), chr(92) + chr(34))}"')
        elif isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        else:
            lines.append(f"{key} = {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path