from pathlib import Path

from forge_agent.config import load_settings
from forge_agent.core.agent import Agent
from forge_agent.models.base import ModelResponse, ToolCall
from forge_agent.ui.approval import ApprovalManager


class FakeProvider:
    model_name = "fake"

    def __init__(self):
        self.calls = 0

    def generate(self, messages, tools=None, *, temperature=0.2, max_tokens=4096):
        self.calls += 1
        if self.calls == 1:
            return ModelResponse(tool_calls=[ToolCall("call-1", "write_file", {"path": "hello.txt", "content": "hello"})])
        return ModelResponse(content="Created hello.txt and finished.")

    def stream(self, *args, **kwargs):
        yield "done"

    def supports_tools(self):
        return True


def test_agent_executes_approved_tool(tmp_path: Path):
    settings = load_settings(cwd=tmp_path, overrides={"max_iterations": 4}, approve_all=True)
    state = Agent(settings, provider=FakeProvider(), approval=ApprovalManager(approve_all=True)).run("Create a hello file")
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert state.final_response == "Created hello.txt and finished."
    assert state.tool_calls[0]["name"] == "write_file"