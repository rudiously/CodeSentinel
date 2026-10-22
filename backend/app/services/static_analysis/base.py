"""Isolated static-tool boundary. Scanned source is data, never executed."""

import json
from pathlib import Path
import shutil
import subprocess
from typing import Literal
from tempfile import TemporaryDirectory

from shared.http import ServiceError
from shared.schemas import Finding, Language


def run_tool(
    argv: list[str], timeout: float, output_path: Path, max_output_bytes: int = 2000000
) -> str:
    try:
        with output_path.open("wb") as output:
            process = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
                shell=False,
                cwd=output_path.parent,
            )
        if process.returncode not in {0, 1}:
            raise ServiceError(
                "STATIC_ANALYSIS_FAILED",
                "Static analyzer reported an operational error",
            )
        if output_path.stat().st_size > max_output_bytes:
            raise ServiceError(
                "STATIC_OUTPUT_TOO_LARGE", "Static analyzer output exceeded limit"
            )
        return output_path.read_text()
    except subprocess.TimeoutExpired:
        raise ServiceError("STATIC_TIMEOUT", "Static analyzer timed out") from None
    except OSError:
        raise ServiceError(
            "STATIC_UNAVAILABLE", "Static analyzer is unavailable"
        ) from None


SEVERITY: dict[str, Literal["High", "Medium", "Low"]] = {
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
}


def bandit(code: str, file: str, timeout: float = 15) -> list[Finding]:
    executable = shutil.which("bandit")
    if executable is None:
        raise ServiceError("STATIC_UNAVAILABLE", "Bandit is not installed")
    with TemporaryDirectory(prefix="codesentinel-") as directory:
        source = Path(directory) / "source.py"
        source.write_text(code)
        text = run_tool(
            [executable, "-q", "-f", "json", str(source)],
            timeout,
            Path(directory) / "output.json",
        )
        try:
            data = json.loads(text)
            if data.get("errors"):
                raise ValueError("Incomplete analysis")
            return [
                Finding(
                    file=file,
                    rule=item["test_id"],
                    severity=SEVERITY[item["issue_severity"]],
                    line=item["line_number"],
                    message=f"Bandit rule {item['test_id']} reported a {item['issue_severity'].lower()} severity finding; review the referenced line",
                )
                for item in data["results"]
            ]
        except (ValueError, KeyError, TypeError):
            raise ServiceError(
                "STATIC_INVALID_RESPONSE", "Bandit output is incomplete or invalid"
            ) from None


def analyze(
    code: str, language: Language, file: str, mode: str = "external"
) -> list[Finding]:
    if mode == "builtin-python" and language == "python":
        from backend.app.services.static_analysis.python_rules import analyze_python

        return analyze_python(code, file)
    if language == "python":
        return bandit(code, file)
    from backend.app.services.static_analysis.cppcheck_runner import cppcheck

    return cppcheck(code, file, language)
