from pathlib import Path
from unittest.mock import patch
import subprocess

import pytest

from backend.app.services.static_analysis.base import analyze, bandit, run_tool
from shared.http import ServiceError


def test_offline_rules_never_execute_source(tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    source = f'def bad(value):\n    open({str(marker)!r}, "w").write("bad")\n    return eval(value)\n'
    findings = analyze(source, "python", "bad.py", "builtin-python")
    assert findings[0].severity == "High"
    assert findings[0].line == 3
    assert not marker.exists()
    assert (
        analyze(
            "def add(a,b):\n    return a+b\n", "python", "clean.py", "builtin-python"
        )
        == []
    )


def test_missing_tool_is_error() -> None:
    with (
        patch("shutil.which", return_value=None),
        pytest.raises(ServiceError, match="Bandit"),
    ):
        bandit("pass", "safe.py")


def test_bandit_normalization_and_fixed_argv() -> None:
    def fake(argv: list[str], timeout: float, output_path: Path) -> str:
        assert argv[1:4] == ["-q", "-f", "json"]
        assert Path(argv[-1]).name == "source.py"
        assert Path(argv[-1]).read_text() == "eval(x)"
        return '{"errors":[],"results":[{"test_id":"B307","issue_severity":"MEDIUM","line_number":1,"issue_text":"eval call"}]}'

    with (
        patch("shutil.which", return_value="/usr/bin/bandit"),
        patch("backend.app.services.static_analysis.base.run_tool", side_effect=fake),
    ):
        findings = bandit("eval(x)", "user;$(bad).py")
    assert findings[0].severity == "Medium" and findings[0].rule == "B307"


def test_subprocess_timeout_maps_to_error(tmp_path: Path) -> None:
    with (
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["tool"], 1)),
        pytest.raises(ServiceError, match="timed out"),
    ):
        run_tool(["tool"], 1, tmp_path / "output")
