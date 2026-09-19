"""Small compatibility wrapper for callers that want an explicit loop object."""

from __future__ import annotations

from forge_agent.core.agent import Agent


class AgentLoop:
    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    def run(self, request: str):
        return self.agent.run(request)