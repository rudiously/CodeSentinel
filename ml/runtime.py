"""Shared tokenization; SMOKE uses a tiny character vocabulary, never CodeBERT."""

from pathlib import Path
from typing import Any

import torch


class SmokeTokenizer:
    def __call__(
        self, codes: str | list[str], max_length: int = 64, **kwargs: Any
    ) -> dict[str, torch.Tensor]:
        values = [codes] if isinstance(codes, str) else codes
        encoded = []
        masks = []
        for code in values:
            ids = (
                [0]
                + [4 + (ord(character) % 256) for character in code[: max_length - 2]]
                + [2]
            )
            mask = [1] * len(ids)
            encoded.append(ids + [1] * (max_length - len(ids)))
            masks.append(mask + [0] * (max_length - len(mask)))
        result = {
            "input_ids": torch.tensor(encoded, dtype=torch.long),
            "attention_mask": torch.tensor(masks, dtype=torch.long),
        }
        if kwargs.get("return_offsets_mapping"):
            result["offset_mapping"] = torch.tensor(
                [
                    [(0, 0)]
                    + [(i, i + 1) for i in range(min(len(code), max_length - 2))]
                    + [(0, 0)] * (max_length - 1 - min(len(code), max_length - 2))
                    for code in values
                ],
                dtype=torch.long,
            )
        return result


def tokenizer_for(directory: Path, kind: str) -> Any:
    if kind == "SMOKE":
        return SmokeTokenizer()
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        str(directory / "tokenizer"), local_files_only=True, use_fast=True
    )
