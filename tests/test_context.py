from pathlib import Path

from forge_agent.context import ContextManager


def test_context_ignores_generated_directories(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def main(): pass\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "secret.js").write_text("ignore me", encoding="utf-8")
    context, files = ContextManager(tmp_path).build("explain app.py")
    assert "src/app.py" in context
    assert "node_modules" not in context
    assert any(path.name == "app.py" for path in files)