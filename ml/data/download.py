"""Fetch verified CodeXGLUE Devign dataset, record exact resolved revision and date."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

DATASET_ID = "google/code_x_glue_cc_defect_detection"
SOURCE = "https://huggingface.co/datasets/google/code_x_glue_cc_defect_detection"


def download(output: Path) -> None:
    from datasets import load_dataset
    from huggingface_hub import HfApi

    info: Any = HfApi().dataset_info(DATASET_ID)
    data: Any = load_dataset(DATASET_ID, revision=info.sha)
    output.mkdir(parents=True, exist_ok=True)
    counts = {}
    for split in ("train", "validation", "test"):
        records = [
            {
                "code": item["func"],
                "label": int(item["target"]),
                "source_split": split,
                "project": item.get("project"),
                "id": item.get("idx"),
            }
            for item in data[split]
        ]
        (output / f"{split}.jsonl").write_text(
            "".join(json.dumps(item) + "\n" for item in records)
        )
        counts[split] = len(records)
    (output / "provenance.json").write_text(
        json.dumps(
            {
                "dataset_id": DATASET_ID,
                "revision": info.sha,
                "source": SOURCE,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "license": "C-UDA (upstream CodeXGLUE; review original source code licenses)",
                "counts": counts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("ml/data/raw"))
    download(parser.parse_args().output)
