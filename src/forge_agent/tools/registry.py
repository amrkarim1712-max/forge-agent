from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from forge_agent.permissions import Decision, PermissionManager
from forge_agent.security import redact_data


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., dict[str, Any]]
    permission: Decision
    timeout: int | None = None

    def model_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


class ToolRegistry:
    def __init__(self, permission_manager: PermissionManager | None = None) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self.permissions = permission_manager or PermissionManager()

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def definitions(self) -> list[dict[str, Any]]:
        return [tool.model_definition() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        spec = self.get(name)
        if spec is None:
            return {"ok": False, "error": f"Unknown tool: {name}"}
        try:
            self._validate_arguments(spec, arguments)
            return redact_data({"ok": True, "result": spec.handler(**arguments)})
        except Exception as exc:  # tool failures become model-observable results
            return redact_data({"ok": False, "error": str(exc)})

    @staticmethod
    def _validate_arguments(spec: ToolSpec, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object.")
        schema = spec.input_schema
        required = schema.get("required", [])
        missing = [name for name in required if name not in arguments]
        if missing:
            raise ValueError(f"Missing required tool argument(s): {', '.join(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(arguments) - set(properties))
            if unknown:
                raise ValueError(f"Unknown tool argument(s): {', '.join(unknown)}")
        for name, value in arguments.items():
            definition = properties.get(name, {})
            expected = definition.get("type")
            valid = {
                "string": isinstance(value, str),
                "integer": isinstance(value, int) and not isinstance(value, bool),
                "array": isinstance(value, list),
                "object": isinstance(value, dict),
                "boolean": isinstance(value, bool),
            }.get(expected, True)
            if not valid:
                raise ValueError(f"Tool argument '{name}' must be a {expected}.")
            if isinstance(value, str) and len(value) > 2_000_000:
                raise ValueError(f"Tool argument '{name}' is too large.")

    def execute_many(self, calls: list[tuple[str, dict[str, Any]]], *, max_workers: int = 4) -> list[dict[str, Any]]:
        """Run only SAFE calls in parallel; callers must serialize writes."""
        if any(self.permissions.classify_tool(name) != Decision.SAFE for name, _ in calls):
            raise ValueError("Parallel execution is limited to SAFE tools.")
        with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
            return list(pool.map(lambda item: self.execute(*item), calls))