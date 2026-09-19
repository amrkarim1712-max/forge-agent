from pathlib import Path
import os

from forge_agent.config import load_settings
from forge_agent.context import ContextManager
from forge_agent.core.agent import Agent
from forge_agent.core.state import AgentPhase
from forge_agent.models.base import ModelResponse, ToolCall
from forge_agent.models.compatible import OpenAICompatibleProvider
from forge_agent.security import redact_text
from forge_agent.tools.filesystem import register_filesystem_tools
from forge_agent.tools.registry import ToolRegistry
from forge_agent.tools.terminal import register_terminal_tools
from forge_agent.ui.approval import ApprovalManager


class RepairProvider:
    model_name = "fake"

    def __init__(self):
        self.calls = 0

    def generate(self, messages, tools=None, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return ModelResponse(tool_calls=[ToolCall("1", "write_file", {"path": "test_sample.py", "content": "def test_ok():\n    assert False\n"})])
        if self.calls == 2:
            return ModelResponse(content="I need to verify the change before finishing.")
        if self.calls == 3:
            return ModelResponse(tool_calls=[ToolCall("3", "edit_file", {"path": "test_sample.py", "old_text": "assert False", "new_text": "assert True"})])
        return ModelResponse(content="Repaired and verified.")

    def stream(self, *args, **kwargs):
        yield "done"

    def supports_tools(self):
        return True


def test_agent_repairs_a_failing_test(tmp_path: Path):
    settings = load_settings(cwd=tmp_path, overrides={"max_iterations": 6, "max_repair_attempts": 2}, approve_all=True)
    state = Agent(settings, provider=RepairProvider(), approval=ApprovalManager(True)).run("Create and verify a passing test")
    assert state.phase == AgentPhase.COMPLETE
    assert state.repair_attempts == 1
    assert state.verification_results[0]["passed"] is True


def test_dry_run_does_not_write(tmp_path: Path):
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path, dry_run=True)
    result = registry.execute("write_file", {"path": "planned.txt", "content": "no write"})
    assert result["result"]["dry_run"] is True
    assert not (tmp_path / "planned.txt").exists()


def test_context_filters_secrets_and_binary_files(tmp_path: Path):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret", encoding="utf-8")
    (tmp_path / "certificate.pem").write_text("private", encoding="utf-8")
    (tmp_path / "image.bin").write_bytes(b"\x00\x01\x02")
    (tmp_path / "app.py").write_text("def app(): pass\n", encoding="utf-8")
    context, _ = ContextManager(tmp_path).build("find app")
    assert "app.py" in context
    assert ".env" not in context
    assert "certificate.pem" not in context
    assert "image.bin" not in context


def test_unified_patch_and_file_lifecycle(tmp_path: Path):
    (tmp_path / "old.txt").write_text("before\n", encoding="utf-8")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    patch = "--- a/old.txt\n+++ b/old.txt\n@@ -1,1 +1,1 @@\n-before\n+after\n"
    assert registry.execute("apply_patch", {"patch": patch})["ok"]
    assert (tmp_path / "old.txt").read_text(encoding="utf-8") == "after\n"
    assert registry.execute("move_file", {"source": "old.txt", "destination": "new.txt"})["ok"]
    assert registry.execute("delete_file", {"path": "new.txt"})["ok"]


def test_provider_retries_transient_status(monkeypatch):
    import httpx

    class Response:
        status_code = 500
        text = "server error"

        def raise_for_status(self):
            raise httpx.HTTPStatusError("temporary", request=None, response=self)

    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 2:
            return Response()

        class Good:
            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

        return Good()

    monkeypatch.setattr("httpx.post", fake_post)
    provider = OpenAICompatibleProvider(
        api_key="test",
        base_url="https://example.test/v1",
        model_name="test",
        retry_attempts=2,
        retry_backoff=0,
    )
    response = provider.generate([{"role": "user", "content": "hi"}])
    assert response.content == "ok"
    assert calls["count"] == 2


def test_security_redacts_secrets_and_rejects_invalid_tool_arguments(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FORGE_TEST_SECRET", "super-secret-value")
    assert "super-secret-value" not in redact_text("token=super-secret-value")

    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    unknown = registry.execute("read_file", {"path": ".", "unexpected": True})
    wrong_type = registry.execute("read_file", {"path": 42})
    assert unknown["ok"] is False
    assert "Unknown tool argument" in unknown["error"]
    assert wrong_type["ok"] is False
    assert "must be a string" in wrong_type["error"]


def test_terminal_output_is_redacted(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FORGE_TEST_TOKEN", "token-value-that-must-not-leak")
    registry = ToolRegistry()
    register_terminal_tools(registry, tmp_path, timeout=10)
    result = registry.execute("run_command", {"command": "printf 'TOKEN=token-value-that-must-not-leak'"})
    assert result["ok"] is True
    assert "token-value-that-must-not-leak" not in str(result)
    assert "[REDACTED]" in result["result"]["stdout"]