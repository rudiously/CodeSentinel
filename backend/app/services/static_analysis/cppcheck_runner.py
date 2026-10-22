from pathlib import Path
import shutil
import subprocess
from typing import Literal
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from shared.http import ServiceError
from shared.schemas import Finding, Language


SEVERITY: dict[str, Literal["High", "Medium", "Low"]] = {
    "error": "High",
    "warning": "Medium",
    "style": "Low",
    "performance": "Low",
    "portability": "Low",
    "information": "Low",
}


def cppcheck(
    code: str, file: str, language: Language, timeout: float = 15
) -> list[Finding]:
    executable = shutil.which("cppcheck")
    if executable is None:
        raise ServiceError("STATIC_UNAVAILABLE", "cppcheck is not installed")
    with TemporaryDirectory(prefix="codesentinel-") as directory:
        source = Path(directory) / ("source.cpp" if language == "cpp" else "source.c")
        source.write_text(code)
        output = Path(directory) / "output.xml"
        try:
            with output.open("wb") as stream:
                result = subprocess.run(
                    [
                        executable,
                        "--xml",
                        "--xml-version=2",
                        "--enable=warning,style,performance,portability",
                        "--error-exitcode=1",
                        str(source),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=stream,
                    timeout=timeout,
                    check=False,
                    shell=False,
                    cwd=directory,
                )
            if result.returncode not in {0, 1} or output.stat().st_size > 2000000:
                raise ServiceError(
                    "STATIC_ANALYSIS_FAILED", "cppcheck failed or output exceeded limit"
                )
            root = ElementTree.fromstring(output.read_text())
            findings = []
            for error in root.findall("./errors/error"):
                if error.get("id") in {"syntaxError", "internalError"}:
                    raise ServiceError(
                        "STATIC_ANALYSIS_FAILED", "cppcheck could not analyze source"
                    )
                for location in error.findall("location"):
                    findings.append(
                        Finding(
                            file=file,
                            rule=error.get("id", "unknown"),
                            severity=SEVERITY.get(error.get("severity", ""), "Low"),
                            line=max(1, int(location.get("line", "1"))),
                            message=f"cppcheck rule {error.get('id', 'unknown')} reported a finding; review the referenced line",
                        )
                    )
            return findings
        except subprocess.TimeoutExpired:
            raise ServiceError("STATIC_TIMEOUT", "cppcheck timed out") from None
        except (OSError, ValueError, ElementTree.ParseError):
            raise ServiceError(
                "STATIC_INVALID_RESPONSE", "cppcheck failed or returned invalid output"
            ) from None
