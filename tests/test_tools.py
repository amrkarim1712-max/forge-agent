from pathlib import Path

from forge_agent.permissions import Decision, PermissionManager
from forge_agent.tools.filesystem import register_filesystem_tools
from forge_agent.tools.registry import ToolRegistry


def test_filesystem_tools_read_write_edit_search(tmp_path: Path):
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    assert registry.execute("write_file", {"path": "src/app.py", "content": "print('hello')"})["ok"]
    read = registry.execute("read_file", {"path": "src/app.py"})
    assert read["result"]["content"] == "print('hello')"
    edited = registry.execute("edit_file", {"path": "src/app.py", "old_text": "hello", "new_text": "world"})
    assert edited["ok"]
    found = registry.execute("search_files", {"query": "world"})
    assert found["result"]["matches"][0]["path"] == "src/app.py"


def test_filesystem_rejects_traversal(tmp_path: Path):
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    result = registry.execute("read_file", {"path": "../secret.txt"})
    assert result["ok"] is False
    assert "outside" in result["error"]


def test_edit_rejects_ambiguous_text(tmp_path: Path):
    (tmp_path / "app.py").write_text("x\nx\n", encoding="utf-8")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    result = registry.execute("edit_file", {"path": "app.py", "old_text": "x", "new_text": "y"})
    assert result["ok"] is False
    assert "ambiguous" in result["error"]


def test_command_classification():
    manager = PermissionManager()
    assert manager.classify_command("git status") == Decision.SAFE
    assert manager.classify_command("rm -rf build") == Decision.REVIEW
    assert manager.classify_command("sudo rm -rf /") == Decision.BLOCKED