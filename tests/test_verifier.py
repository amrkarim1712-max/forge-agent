from pathlib import Path

from forge_agent.planning.verifier import Verifier


def test_verifier_reports_passing_pytest(tmp_path: Path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "test_sample.py").write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    result = Verifier(tmp_path, timeout=30).run()
    assert result.passed is True
    assert result.command == "python -m pytest"