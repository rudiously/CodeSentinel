"""Measured binary metrics; the caller must supply provenance with every output."""

from typing import Any
from math import isfinite

from shared.schemas import Decision

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)


def evaluate(
    labels: list[int],
    probabilities: list[float],
    threshold: float = 0.5,
    *,
    predictions: list[int] | None = None,
) -> dict[str, Any]:
    if (
        not labels
        or len(labels) != len(probabilities)
        or any(label not in (0, 1) for label in labels)
        or any(not isfinite(p) or p < 0 or p > 1 for p in probabilities)
        or not isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("Invalid evaluation inputs")
    if predictions is not None and (
        len(predictions) != len(labels)
        or any(value not in (0, 1) for value in predictions)
    ):
        raise ValueError("Invalid explicit predictions")
    predicted = (
        predictions
        if predictions is not None
        else [int(p >= threshold) for p in probabilities]
    )
    precision, recall, thresholds = precision_recall_curve(labels, probabilities)
    return {
        "accuracy": float(accuracy_score(labels, predicted)),
        "precision": float(precision_score(labels, predicted, zero_division=0)),
        "recall": float(recall_score(labels, predicted, zero_division=0)),
        "f1": float(f1_score(labels, predicted, zero_division=0)),
        "confusion_matrix": confusion_matrix(labels, predicted, labels=[0, 1]).tolist(),
        "pr_curve": {
            "basis": "raw_scores_without_decision_safety_overrides",
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "thresholds": thresholds.tolist(),
        },
        "prediction_source": (
            "decisions" if predictions is not None else "score_threshold"
        ),
        "threshold": None if predictions is not None else threshold,
        "count": len(labels),
    }


def evaluate_decisions(
    labels: list[int], scores: list[float], decisions: list[Decision]
) -> dict[str, Any]:
    if any(decision == "ERROR" for decision in decisions):
        raise ValueError("Cannot report a failed analysis as a binary prediction")
    return {
        "flagged_WARN_or_BLOCK": evaluate(
            labels,
            scores,
            predictions=[int(decision in {"WARN", "BLOCK"}) for decision in decisions],
        ),
        "blocked_only": evaluate(
            labels,
            scores,
            predictions=[int(decision == "BLOCK") for decision in decisions],
        ),
    }
