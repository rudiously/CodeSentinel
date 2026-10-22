import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from sklearn.model_selection import train_test_split

from ml.data.clean import clean, code_hash


def split_records(
    records: list[dict[str, Any]], seed: int = 42
) -> dict[str, list[dict[str, Any]]]:
    train, held = train_test_split(
        records,
        test_size=0.2,
        random_state=seed,
        stratify=[r["label"] for r in records],
    )
    validation, test = train_test_split(
        held, test_size=0.5, random_state=seed, stratify=[r["label"] for r in held]
    )
    result = {"train": train, "validation": validation, "test": test}
    hashes = [{code_hash(r["code"]) for r in result[key]} for key in result]
    if hashes[0] & hashes[1] or hashes[0] & hashes[2] or hashes[1] & hashes[2]:
        raise ValueError("Cross-split leakage detected")
    return result


def prepare(raw: Path, output: Path, seed: int = 42) -> dict[str, Any]:
    records = [
        json.loads(line)
        for path in sorted(raw.glob("*.jsonl"))
        for line in path.read_text().splitlines()
        if line
    ]
    cleaned, report = clean(records)
    splits = split_records(cleaned, seed)
    output.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, items in splits.items():
        content = "".join(json.dumps(item, sort_keys=True) + "\n" for item in items)
        (output / f"{name}.jsonl").write_text(content)
        hashes[name] = hashlib.sha256(content.encode()).hexdigest()
    result = {
        "cleaning": report,
        "counts": {name: len(items) for name, items in splits.items()},
        "hashes": hashes,
        "dataset_hash": hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode()
        ).hexdigest(),
        "seed": seed,
        "split_method": "stratified held-out samples, not repositories",
        "proposed_counts_not_assumed": [21808, 2724, 2726],
    }
    (output / "report.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("ml/data/raw"))
    parser.add_argument("--output", type=Path, default=Path("ml/data/processed"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(prepare(args.raw, args.output, args.seed), indent=2))
