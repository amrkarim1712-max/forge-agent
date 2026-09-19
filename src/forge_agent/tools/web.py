from __future__ import annotations

from typing import Any

import httpx

from forge_agent.core.errors import ToolError
from forge_agent.permissions import Decision
from forge_agent.security import redact_data
from .registry import ToolRegistry, ToolSpec


def register_web_tool(registry: ToolRegistry, endpoint: str, *, timeout: int = 30) -> None:
    """Use a user-configured search endpoint; never invents results or credentials."""
    def web_search(query: str, max_results: int = 5):
        try:
            response = httpx.get(endpoint, params={"q": query, "limit": max_results}, timeout=timeout)
            response.raise_for_status()
            data: Any = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ToolError(f"Configured web search failed: {exc}") from exc
        bounded = redact_data(data)
        encoded = str(bounded)
        return {"query": query, "source": "configured_web_search", "results": encoded[:16000], "truncated": len(encoded) > 16000}

    registry.register(ToolSpec(
        "web_search",
        "Search the web through the explicitly configured endpoint. Results are external, not repository facts.",
        {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["query"], "additionalProperties": False},
        web_search,
        Decision.REVIEW,
        timeout,
    ))