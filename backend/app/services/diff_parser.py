"""Strict unified-diff parsing. A diff is not full source: callers must supply blobs."""

from dataclasses import dataclass, field
import re
from pathlib import PurePosixPath

from shared.http import ServiceError

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass
class ChangedFile:
    path: str
    changed_lines: set[int] = field(default_factory=set)
    deleted: bool = False


def safe_path(path: str) -> str:
    parsed = PurePosixPath(path)
    if (
        not path
        or parsed.is_absolute()
        or ".." in parsed.parts
        or "\\" in path
        or any(ord(c) < 32 for c in path)
    ):
        raise ServiceError("INVALID_PATH", "Invalid repository-relative path", 422)
    return str(parsed)


def parse_diff(diff: str, max_files: int = 50) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    current: ChangedFile | None = None
    old_path = ""
    line_no = 0
    old_left = new_left = 0
    in_hunk = False
    for line in diff.splitlines():
        if in_hunk and (old_left or new_left):
            if line.startswith("\\ No newline"):
                continue
            prefix = line[:1]
            if prefix not in {" ", "+", "-"}:
                raise ServiceError("INVALID_DIFF", "Unexpected hunk content", 422)
            if prefix in {" ", "-"}:
                old_left -= 1
            if prefix in {" ", "+"}:
                new_left -= 1
                if prefix == "+" and current:
                    current.changed_lines.add(line_no)
                line_no += 1
            if old_left < 0 or new_left < 0:
                raise ServiceError(
                    "INVALID_DIFF", "Hunk counts do not match content", 422
                )
            continue
        match = HUNK.match(line)
        if match:
            if current is None:
                raise ServiceError("INVALID_DIFF", "Hunk missing file header", 422)
            line_no = int(match[3])
            old_left = int(match[2]) if match[2] is not None else 1
            new_left = int(match[4]) if match[4] is not None else 1
            in_hunk = True
            continue
        if line.startswith("--- "):
            raw = line[4:].split("\t")[0]
            old_path = raw[2:] if raw.startswith("a/") else raw
        elif line.startswith("+++ "):
            raw = line[4:].split("\t")[0]
            deleted = raw == "/dev/null"
            path = old_path if deleted else (raw[2:] if raw.startswith("b/") else raw)
            current = ChangedFile(safe_path(path), deleted=deleted)
            files.append(current)
            if len(files) > max_files:
                raise ServiceError(
                    "TOO_MANY_FILES", "Diff exceeds configured file limit", 413
                )
    if old_left or new_left:
        raise ServiceError("INVALID_DIFF", "Truncated diff hunk", 422)
    if not files:
        raise ServiceError("INVALID_DIFF", "No supported unified diff files", 422)
    return files
