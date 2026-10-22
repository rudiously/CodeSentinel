import pytest

from backend.app.services.diff_parser import parse_diff, safe_path
from backend.app.services.function_extractor import extract_functions
from shared.http import ServiceError


def test_python_function_ranges_decorators_and_unicode() -> None:
    code = '@wrap\ndef hello():\n    text = "नमस्कार"\n    return text\n\nasync def second():\n    return 2\n'
    functions = extract_functions(code, "python", "safe.py", allow_python_ast=True)
    assert [(f.name, f.start_line, f.end_line) for f in functions] == [
        ("hello", 1, 4),
        ("second", 6, 7),
    ]
    assert functions[0].code.startswith("@wrap")


def test_invalid_python_is_not_guessed() -> None:
    with pytest.raises(ServiceError):
        extract_functions("def invalid(", "python", "bad.py", allow_python_ast=True)


def test_diff_line_mapping_and_deletion() -> None:
    diff = "--- a/a.py\n+++ b/a.py\n@@ -10,2 +10,3 @@\n x\n-y\n+z\n+q\n"
    files = parse_diff(diff)
    assert files[0].path == "a.py"
    assert files[0].changed_lines == {11, 12}
    deleted = parse_diff("--- a/old.c\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n")
    assert deleted[0].deleted


@pytest.mark.parametrize("path", ["../x", "/tmp/x", "a/../../x", "a\\b", "x\x00"])
def test_paths_cannot_escape(path: str) -> None:
    with pytest.raises(ServiceError):
        safe_path(path)


def test_truncated_diff_fails() -> None:
    with pytest.raises(ServiceError):
        parse_diff("--- a/a.py\n+++ b/a.py\n@@ -1,2 +1,2 @@\n x\n")
