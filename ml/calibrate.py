"""Calibration and recall-oriented classification threshold: VALIDATION only."""

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.metrics import precision_score, recall_score
from typing import Any


def probabilities(logits: Any, temperature: float = 1.0) -> Any:
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("Temperature must be positive")
    scaled = np.asarray(logits, dtype=float) / temperature
    exp = np.exp(scaled - scaled.max(axis=1, keepdims=True))
    return exp[:, 1] / exp.sum(axis=1)


def calibrate(
    logits: Any,
    labels: list[int],
    split: str = "validation",
    recall_target: float = 0.8,
) -> dict[str, float]:
    if split != "validation":
        raise ValueError("Calibration may only use validation data")
    array = np.asarray(logits, dtype=float)
    y = np.asarray(labels, dtype=int)
    if (
        array.shape != (len(y), 2)
        or len(y) == 0
        or not np.isfinite(array).all()
        or set(labels) != {0, 1}
    ):
        raise ValueError("Need finite binary validation logits with both classes")

    def nll(temp: float) -> float:
        p = np.clip(probabilities(array, temp), 1e-8, 1 - 1e-8)
        return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

    fitted = minimize_scalar(nll, bounds=(0.05, 10), method="bounded")
    if not fitted.success:
        raise ValueError("Temperature optimization failed")
    temperature = float(fitted.x)
    p = probabilities(array, temperature)
    candidates = []
    for threshold in sorted(set([0.0, 0.5, 1.0] + [float(v) for v in p])):
        predicted = p >= threshold
        recall = float(recall_score(y, predicted, zero_division=0))
        precision = float(precision_score(y, predicted, zero_division=0))
        if recall >= recall_target:
            candidates.append((precision, threshold, recall))
    precision, threshold, recall = max(candidates)
    return {
        "temperature": temperature,
        "classification": threshold,
        "validation_recall": recall,
        "validation_precision": precision,
        "recall_target": recall_target,
    }
