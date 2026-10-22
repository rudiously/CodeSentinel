"""Seeded CodeBERT training; CPU SMOKE uses tiny randomly initialized RoBERTa."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
from typing import Any, Callable, cast

import numpy as np
import torch
import yaml

from ml.calibrate import calibrate, probabilities
from ml.evaluate import evaluate
from ml.export import export
from ml.register import git_commit, write_metadata, register_version
from ml.runtime import SmokeTokenizer


def _smoke_records() -> dict[str, list[dict[str, Any]]]:
    # Deliberately synthetic; disjoint function names and tiny sample counts.
    return {
        split: [
            {
                "code": f"int {split}_f{i}(){{"
                + (f"char b[8];strcpy(b,input{i});" if i % 2 else f"return {i};")
                + "}",
                "label": i % 2,
            }
            for i in range(count)
        ]
        for split, count in [("train", 16), ("validation", 8), ("test", 8)]
    }


def train(config_path: Path) -> dict[str, Any]:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        RobertaConfig,
        RobertaForSequenceClassification,
    )
    import mlflow

    config: dict[str, Any] = yaml.safe_load(config_path.read_text())
    seed = int(config["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    smoke = config["mode"] == "smoke"
    kind = "SMOKE" if smoke else "TRAINED"
    if smoke:
        data = _smoke_records()
        tokenizer: Any = SmokeTokenizer()
        architecture = cast(Callable[..., Any], RobertaConfig)(
            vocab_size=260,
            hidden_size=32,
            num_hidden_layers=1,
            num_attention_heads=2,
            intermediate_size=64,
            max_position_embeddings=514,
            num_labels=2,
            hidden_dropout_prob=0.0,
            attention_probs_dropout_prob=0.0,
            pad_token_id=1,
        )
        architecture._attn_implementation = "eager"
        model: Any = cast(Callable[..., Any], RobertaForSequenceClassification)(
            architecture
        )
        dataset_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
    else:
        processed = Path(config["processed_dir"])
        data = {
            split: [
                json.loads(line)
                for line in (processed / f"{split}.jsonl").read_text().splitlines()
                if line
            ]
            for split in ("train", "validation", "test")
        }
        dataset_hash = json.loads((processed / "report.json").read_text())[
            "dataset_hash"
        ]
        tokenizer = AutoTokenizer.from_pretrained(config["model_id"], use_fast=True)
        model = cast(
            Callable[..., Any], AutoModelForSequenceClassification.from_pretrained
        )(config["model_id"], num_labels=2, attn_implementation="eager")
    device = torch.device(
        "cpu" if smoke else "cuda" if torch.cuda.is_available() else "cpu"
    )
    model.to(device)
    max_length = int(config["max_length"])

    def encode(records: list[dict[str, Any]]) -> Any:
        return tokenizer(
            [r["code"] for r in records],
            max_length=max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

    encoded = {split: encode(items) for split, items in data.items()}
    encoded = {
        split: {key: value.to(device) for key, value in batch.items()}
        for split, batch in encoded.items()
    }
    labels = {
        split: torch.tensor(
            [r["label"] for r in items], dtype=torch.long, device=device
        )
        for split, items in data.items()
    }

    def collect_logits(split: str) -> Any:
        # Validation/test must be batched too; a full 2,700-function forward would OOM.
        chunks = []
        batch_size = int(config["batch_size"])
        with torch.no_grad():
            for start in range(0, len(data[split]), batch_size):
                batch = {
                    key: value[start : start + batch_size]
                    for key, value in encoded[split].items()
                }
                chunks.append(model(**batch).logits.detach().cpu())
        return torch.cat(chunks).numpy()

    counts = torch.bincount(labels["train"], minlength=2)
    if (counts == 0).any():
        raise ValueError("Training requires both classes")
    weights = (
        (len(data["train"]) / (2 * counts.float()))
        if config.get("class_weighting")
        else None
    )
    criterion = torch.nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(config["learning_rate"]))
    output = Path(config["output"])
    if smoke and output.exists() and any(output.iterdir()):
        output = output.with_name(
            output.name + "-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        )
    if output.exists() and any(output.iterdir()):
        raise ValueError(
            "Output artifact already exists; select a new version instead of overwriting"
        )
    output.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(config["mlflow_uri"])
    mlflow.set_experiment("CodeSentinel-CodeBERT")
    with mlflow.start_run(run_name=f"{kind}-{output.name}") as run:
        mlflow.log_params(
            {
                **config,
                "artifact_kind": kind,
                "device": str(device),
                "dataset_hash": dataset_hash,
                "git_commit": git_commit(),
                "long_function_policy": "truncate",
                "initialization": (
                    "random-tiny-roberta" if smoke else config["model_id"]
                ),
            }
        )
        mlflow.log_artifact(str(config_path))
        best = -1.0
        stale = 0
        best_state = None
        for epoch in range(int(config["epochs"])):
            model.train()
            order = torch.randperm(len(data["train"]), device=device)
            for start in range(0, len(order), int(config["batch_size"])):
                indices = order[start : start + int(config["batch_size"])]
                optimizer.zero_grad()
                logits = model(
                    input_ids=encoded["train"]["input_ids"][indices],
                    attention_mask=encoded["train"]["attention_mask"][indices],
                ).logits
                loss = criterion(logits, labels["train"][indices])
                loss.backward()
                optimizer.step()
            model.eval()
            validation_logits = collect_logits("validation")
            validation = evaluate(
                labels["validation"].tolist(), probabilities(validation_logits).tolist()
            )
            mlflow.log_metric("validation_f1", validation["f1"], step=epoch)
            if validation["f1"] > best:
                best = validation["f1"]
                stale = 0
                best_state = {
                    k: v.detach().cpu().clone() for k, v in model.state_dict().items()
                }
                checkpoint_dir = output.parent / "checkpoints" / output.name
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                torch.save(
                    {
                        "epoch": epoch,
                        "model_state_dict": best_state,
                        "optimizer_state_dict": optimizer.state_dict(),
                        "dataset_hash": dataset_hash,
                        "config": config,
                    },
                    checkpoint_dir / "best.pt",
                )
            else:
                stale += 1
                if stale >= int(config["patience"]):
                    break
        if best_state is None:
            raise ValueError("No checkpoint produced")
        model.load_state_dict(best_state)
        model.eval()
        validation_logits = collect_logits("validation")
        calibration = calibrate(validation_logits, labels["validation"].tolist())
        # Test data is touched only after model selection and calibration freeze.
        test_logits = collect_logits("test")
        measured = evaluate(
            labels["test"].tolist(),
            probabilities(test_logits, calibration["temperature"]).tolist(),
            calibration["classification"],
        )
        parity = export(model.cpu(), tokenizer, output, max_length)
        (output / "tokenizer").mkdir()
        if smoke:
            (output / "tokenizer" / "smoke.json").write_text(
                json.dumps(
                    {
                        "kind": "SMOKE",
                        "vocabulary": "character-modulo-256, collisions possible",
                        "max_length": max_length,
                    }
                )
            )
        else:
            tokenizer.save_pretrained(output / "tokenizer")
        (output / "evaluation.json").write_text(
            json.dumps(
                {"artifact_kind": kind, "synthetic": smoke, "metrics": measured},
                indent=2,
            )
        )
        metadata = write_metadata(
            output,
            {
                "artifact_path": str(output),
                "model_version": output.name,
                "artifact_kind": kind,
                "initialization": (
                    "random-tiny-roberta" if smoke else config["model_id"]
                ),
                "dataset_hash": dataset_hash,
                "metrics": measured,
                "temperature": calibration["temperature"],
                "thresholds": {"classification": calibration["classification"]},
                "calibration": calibration,
                "max_length": max_length,
                "long_function_policy": "truncate",
                "attribution_method": "integrated-gradients",
                "export_parity": parity,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "mlflow_run_id": run.info.run_id,
                "synthetic": smoke,
            },
        )
        mlflow.log_metrics(
            {
                key: float(measured[key])
                for key in ["accuracy", "precision", "recall", "f1"]
            }
        )
        mlflow.log_artifacts(str(output), artifact_path=f"{kind}-artifact")
        registry_version = register_version(
            run.info.run_id, mlflow.get_artifact_uri(f"{kind}-artifact"), kind
        )
        metadata["registry_version"] = registry_version
        (output / "metadata.json").write_text(json.dumps(metadata, indent=2))
        mlflow.log_artifact(
            str(output / "metadata.json"), artifact_path=f"{kind}-artifact"
        )
        mlflow.set_tag(
            "performance_claim",
            (
                "SMOKE ONLY; NOT TRAINED CODEBERT"
                if smoke
                else "held-out samples, not repositories"
            ),
        )
        return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    result = train(parser.parse_args().config)
    print(
        json.dumps(
            {
                "artifact_kind": result["artifact_kind"],
                "model_version": result["model_version"],
                "export_parity": result["export_parity"],
            }
        )
    )
