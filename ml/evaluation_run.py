"""One-command ablation/error/latency report, with validation-only threshold exploration."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from backend.app.services.risk_engine import RiskConfig, score_risk
from backend.app.services.static_analysis.base import analyze
from ml.data.clean import code_hash
from ml.evaluate import evaluate_decisions
from ml.predictor import Predictor
from shared.schemas import Mode


def _records(path: Path) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text().splitlines() if line]
    if not records or any(
        not isinstance(record, dict)
        or not isinstance(record.get("code"), str)
        or not record["code"].strip()
        or record.get("label") not in (0, 1)
        or record.get("language", "c") not in {"c", "cpp", "python"}
        or not isinstance(record.get("synthetic", False), bool)
        for record in records
    ):
        raise ValueError(
            "Evaluation requires nonempty labelled source records with valid provenance"
        )
    return records


def evaluation_provenance(
    metadata: dict[str, Any], records: list[dict[str, Any]]
) -> tuple[bool, str]:
    synthetic = (
        metadata["artifact_kind"] == "SMOKE"
        or bool(metadata.get("synthetic", False))
        or any(record.get("synthetic", False) for record in records)
    )
    claim = (
        "SMOKE PIPELINE VERIFICATION ONLY"
        if metadata["artifact_kind"] == "SMOKE"
        else (
            "SYNTHETIC PIPELINE VERIFICATION ONLY"
            if synthetic
            else "Measured held-out-sample evaluation; repository generalization unvalidated"
        )
    )
    return synthetic, claim


def run(
    artifact: Path,
    test_file: Path,
    output: Path,
    *,
    validation_file: Path | None = None,
    analyzer_mode: str = "external",
) -> dict[str, Any]:
    records = _records(test_file)
    validation = _records(validation_file) if validation_file else []
    if {code_hash(record["code"]) for record in records} & {
        code_hash(record["code"]) for record in validation
    }:
        raise ValueError("Validation/test overlap; refuse threshold exploration")
    predictor = Predictor(artifact)

    def signals(
        records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[float], list[list[Any]], list[float]]:
        probabilities = []
        findings = []
        latencies = []
        for record in records:
            started = perf_counter()
            prediction = predictor.predict(record["code"], record.get("language", "c"))
            static = analyze(
                record["code"],
                record.get("language", "c"),
                (
                    "evaluation.py"
                    if record.get("language") == "python"
                    else "evaluation.c"
                ),
                analyzer_mode,
            )
            probabilities.append(prediction.probability)
            findings.append(static)
            latencies.append(perf_counter() - started)
        return records, probabilities, findings, latencies

    records, p, findings, latency = signals(records)
    labels = [int(r["label"]) for r in records]
    modes: list[Mode] = ["model_only", "static_only", "combined"]
    ablation = {}
    errors = {}
    for mode in modes:
        results = [
            score_risk(probability, static, "evaluation", mode)
            for probability, static in zip(p, findings, strict=True)
        ]
        scores = [result.risk_score or 0.0 for result in results]
        ablation[mode] = evaluate_decisions(
            labels, scores, [result.decision for result in results]
        )
        errors[mode] = [
            {
                "code_hash": code_hash(record["code"]),
                "label": label,
                "decision": result.decision,
                "risk": result.risk_score,
                "category": "false_positive" if label == 0 else "false_negative",
            }
            for record, label, result in zip(records, labels, results, strict=True)
            if (result.decision in {"WARN", "BLOCK"}) != bool(label)
        ]
    sweep = []
    if validation_file:
        validation, vp, vfindings, _ = signals(validation)
        for threshold in [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]:
            config = RiskConfig(warn_threshold=threshold)
            results = [
                score_risk(probability, static, "validation", "combined", config)
                for probability, static in zip(vp, vfindings, strict=True)
            ]
            sweep.append(
                {
                    "validation_only": True,
                    "warn_threshold": threshold,
                    "metrics": evaluate_decisions(
                        [r["label"] for r in validation],
                        [result.risk_score or 0.0 for result in results],
                        [result.decision for result in results],
                    )["flagged_WARN_or_BLOCK"],
                }
            )
    synthetic, claim = evaluation_provenance(predictor.metadata, records + validation)
    result = {
        "artifact_kind": predictor.metadata["artifact_kind"],
        "model_version": predictor.metadata["model_version"],
        "synthetic": synthetic,
        "claim": claim,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "test_file": str(test_file),
        "analyzer_mode": analyzer_mode,
        "ablation": ablation,
        "error_analysis": errors,
        "latency_seconds": {
            "count": len(latency),
            "p50": float(np.percentile(latency, 50)),
            "p95": float(np.percentile(latency, 95)),
            "includes": "local CPU inference and static analysis; excludes HTTP and DB",
        },
        "validation_threshold_sweep": sweep,
        "threshold_policy": "Frozen defaults .35 WARN/.65 BLOCK; sweep is descriptive validation analysis, never tuned on test",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--analyzer-mode", choices=["external", "builtin-python"], default="external"
    )
    args = parser.parse_args()
    result = run(
        args.artifact,
        args.test,
        args.output,
        validation_file=args.validation,
        analyzer_mode=args.analyzer_mode,
    )
    print(
        f"{result['artifact_kind']}: wrote measured ablation, errors and latency; no superiority claim inferred."
    )
