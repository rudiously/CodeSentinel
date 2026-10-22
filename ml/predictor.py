"""Contract A for trusted, manifest-verified TorchScript artifacts."""

import json
import math
from pathlib import Path
from threading import Lock
from typing import Any, Callable, cast

import torch

from ml.register import sha256
from ml.runtime import tokenizer_for
from ml.explain import integrated_gradients
from shared.schemas import Prediction, TokenImportance


class Predictor:
    def __init__(self, directory: Path, explain_steps: int = 8) -> None:
        metadata = json.loads((directory / "metadata.json").read_text())
        if (
            metadata.get("format") != "torchscript"
            or metadata.get("model_file") != "model.pt"
            or metadata.get("artifact_kind") not in {"SMOKE", "TRAINED"}
        ):
            raise ValueError("Unsupported or unlabelled model artifact")
        if not metadata.get("files_sha256") or metadata["files_sha256"].get(
            "model.pt"
        ) != metadata.get("weights_sha256"):
            raise ValueError("Missing or inconsistent weights hash")
        actual_files = {
            str(path.relative_to(directory))
            for path in directory.rglob("*")
            if path.is_file() and path.name != "metadata.json"
        }
        if actual_files != set(metadata["files_sha256"]):
            raise ValueError("Artifact manifest does not cover all files")
        for name, expected in metadata["files_sha256"].items():
            path = (directory / name).resolve()
            if (
                not path.is_relative_to(directory.resolve())
                or not path.is_file()
                or sha256(path) != expected
            ):
                raise ValueError("Artifact SHA256 mismatch or unsafe manifest path")
        self.metadata: dict[str, Any] = metadata
        self.max_length = int(metadata["max_length"])
        self.temperature = float(metadata["temperature"])
        self.threshold = float(metadata["thresholds"]["classification"])
        if (
            not 2 <= self.max_length <= 512
            or not math.isfinite(self.temperature)
            or self.temperature <= 0
            or not 0 <= self.threshold <= 1
        ):
            raise ValueError("Invalid model preprocessing or calibration metadata")
        self.model = cast(Callable[..., Any], torch.jit.load)(
            str(directory / "model.pt"), map_location="cpu"
        ).eval()
        self.tokenizer = tokenizer_for(directory, metadata["artifact_kind"])
        self.lock = Lock()
        self.explain_steps = explain_steps

    def explain(self, code: str) -> list[TokenImportance]:
        if (
            self.explain_steps < 2
            or self.metadata.get("attribution_method") != "integrated-gradients"
        ):
            return []
        encoded = self.tokenizer(
            code,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
            return_offsets_mapping=True,
        )
        with self.lock, torch.enable_grad():
            inputs = self.model.embed(encoded["input_ids"]).detach()

            def forward(value: torch.Tensor) -> torch.Tensor:
                logits: torch.Tensor = self.model.from_embeddings(
                    value, encoded["attention_mask"]
                )
                return logits[:, 1] - logits[:, 0]

            importance = integrated_gradients(
                forward, inputs, steps=self.explain_steps
            ).sum(dim=-1)[0]
        values = importance.detach().tolist()
        offsets = encoded["offset_mapping"][0].tolist()
        denominator = (
            sum(
                abs(value)
                for value, (start, end) in zip(values, offsets, strict=True)
                if start != end
            )
            or 1.0
        )
        return [
            TokenImportance(
                token=code[start:end],
                line=code.count("\n", 0, start) + 1,
                importance=value / denominator,
            )
            for value, (start, end) in zip(values, offsets, strict=True)
            if start != end
        ]

    def predict(self, code: str, language: str = "c") -> Prediction:
        return self.predict_batch([code], language)[0]

    def predict_batch(self, codes: list[str], language: str = "c") -> list[Prediction]:
        if not codes or len(codes) > 32 or any(not c or len(c) > 100000 for c in codes):
            raise ValueError("Prediction input exceeds contract limits")
        if language not in {"c", "cpp", "python"}:
            raise ValueError("Unsupported language")
        with self.lock, torch.no_grad():
            encoded = self.tokenizer(
                codes,
                max_length=self.max_length,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )
            logits = self.model(encoded["input_ids"], encoded["attention_mask"])
            probabilities = torch.softmax(logits / self.temperature, dim=-1)[
                :, 1
            ].tolist()
        return [
            Prediction(
                probability=float(p),
                label="VULNERABLE" if p >= self.threshold else "SAFE",
                token_importance=self.explain(codes[index]),
                model_version=str(self.metadata["model_version"]),
                model_mode="real",
                artifact_kind=self.metadata["artifact_kind"],
            )
            for index, p in enumerate(probabilities)
        ]
