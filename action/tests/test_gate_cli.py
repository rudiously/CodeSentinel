import json
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "decision,expected", [("PASS", 0), ("WARN", 0), ("BLOCK", 1), ("ERROR", 2)]
)
def test_real_dry_run_exit_codes(tmp_path: Path, decision: str, expected: int) -> None:
    data = json.loads(Path("fixtures/scan_report.json").read_text())
    data.update(
        decision=decision,
        risk_score=(
            None
            if decision == "ERROR"
            else 0.9 if decision == "BLOCK" else 0.5 if decision == "WARN" else 0.05
        ),
        errors=["SYNTHETIC test error"] if decision == "ERROR" else [],
    )
    path = tmp_path / "report.json"
    path.write_text(json.dumps(data))
    result = subprocess.run(
        [sys.executable, "-m", "action.gate", "--dry-run", "--report", str(path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == expected, result.stderr
    assert "STUB" in result.stdout
