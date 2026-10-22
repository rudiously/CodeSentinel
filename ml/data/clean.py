"""Exact normalized deduplication; remove all conflicting-label hashes."""

import hashlib
from typing import Any


def normalize(code: str) -> str:
    return code.replace("\r\n", "\n").strip()


def code_hash(code: str) -> str:
    return hashlib.sha256(normalize(code).encode()).hexdigest()


def clean(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    invalid = 0
    for record in records:
        if (
            not isinstance(record.get("code"), str)
            or not normalize(record["code"])
            or record.get("label") not in (0, 1)
        ):
            invalid += 1
            continue
        groups.setdefault(code_hash(record["code"]), []).append(record)
    cleaned = []
    conflicts = duplicates = 0
    for digest, group in sorted(groups.items()):
        if len({int(r["label"]) for r in group}) > 1:
            conflicts += len(group)
            continue
        duplicates += len(group) - 1
        cleaned.append(
            {**group[0], "code": normalize(group[0]["code"]), "code_hash": digest}
        )
    return cleaned, {
        "input": len(records),
        "invalid": invalid,
        "conflicting_label_rows": conflicts,
        "duplicate_rows": duplicates,
        "output": len(cleaned),
    }
