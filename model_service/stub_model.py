"""Deterministic STUB for integration, not a trained vulnerability classifier."""

from typing import TypedDict


class Prediction(TypedDict):
    probability: float
    label: str
    token_importance: list[dict[str, object]]
    model_version: str
    model_mode: str
    artifact_kind: str


def predict(code: str, language: str = "c") -> Prediction:
    markers = ("strcpy(", "eval(", "gets(", "shell=True", "printf(input")
    probability = 0.9 if any(marker in code for marker in markers) else 0.1
    return {
        "probability": probability,
        "label": "VULNERABLE" if probability >= 0.5 else "SAFE",
        "token_importance": [],
        "model_version": "stub-v1",
        "model_mode": "stub",
        "artifact_kind": "STUB",
    }


def predict_batch(codes: list[str], language: str = "c") -> list[Prediction]:
    return [predict(code, language) for code in codes]
