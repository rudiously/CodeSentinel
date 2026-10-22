"""Small offline AST rule set, explicitly NOT Bandit or an equivalent replacement."""

import ast

from shared.http import ServiceError
from shared.schemas import Finding


def analyze_python(code: str, file: str) -> list[Finding]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, RecursionError, ValueError):
        raise ServiceError(
            "STATIC_ANALYSIS_FAILED", "Cannot parse Python source", 422
        ) from None
    findings: list[Finding] = []

    def add(node: ast.AST, rule: str, severity: str, message: str) -> None:
        findings.append(
            Finding.model_validate(
                {
                    "file": file,
                    "rule": rule,
                    "severity": severity,
                    "line": getattr(node, "lineno", 1),
                    "message": message,
                }
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            )
            if name in {"eval", "exec"}:
                add(
                    node,
                    "CS-PY-001",
                    "High",
                    "Dynamic code execution can execute untrusted input",
                )
            if any(
                k.arg == "shell"
                and isinstance(k.value, ast.Constant)
                and k.value.value is True
                for k in node.keywords
            ):
                add(
                    node,
                    "CS-PY-002",
                    "High",
                    "Shell execution can enable command injection",
                )
            if (
                name in {"execute", "executemany"}
                and node.args
                and isinstance(node.args[0], (ast.BinOp, ast.JoinedStr))
            ):
                add(
                    node,
                    "CS-PY-003",
                    "Medium",
                    "Constructed SQL should use parameter binding",
                )
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and node.value.value
        ):
            if any(
                isinstance(t, ast.Name)
                and any(
                    word in t.id.lower()
                    for word in ("password", "secret", "api_key", "token")
                )
                for t in node.targets
            ):
                add(
                    node,
                    "CS-PY-004",
                    "Medium",
                    "Possible hardcoded credential; use environment secrets",
                )
    return sorted(findings, key=lambda f: (f.line, f.rule))
