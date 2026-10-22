"""TorchScript is the CPU export path; numerical parity is mandatory."""

from pathlib import Path
from typing import Any, Callable, cast

import torch
from torch import nn


class LogitsOnly(nn.Module):
    def __init__(self, model: Any) -> None:
        super().__init__()
        self.model = model

    def forward(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor
    ) -> torch.Tensor:
        result: torch.Tensor = self.model(
            input_ids=input_ids, attention_mask=attention_mask, return_dict=False
        )[0]
        return result

    def embed(self, input_ids: torch.Tensor) -> torch.Tensor:
        result: torch.Tensor = self.model.get_input_embeddings()(input_ids)
        return result

    def from_embeddings(
        self, inputs_embeds: torch.Tensor, attention_mask: torch.Tensor
    ) -> torch.Tensor:
        result: torch.Tensor = self.model(
            inputs_embeds=inputs_embeds,
            attention_mask=attention_mask,
            return_dict=False,
        )[0]
        return result


def export(
    model: Any,
    tokenizer: Any,
    directory: Path,
    max_length: int,
    tolerance: float = 1e-4,
) -> dict[str, float]:
    directory.mkdir(parents=True, exist_ok=True)
    wrapper = LogitsOnly(model.eval())
    first = tokenizer(
        ["int add(int a,int b){return a+b;}"],
        max_length=max_length,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )
    example = (first["input_ids"], first["attention_mask"])
    with torch.no_grad():
        embeddings = wrapper.embed(first["input_ids"])
        traced = cast(Callable[..., Any], torch.jit.trace_module)(
            wrapper,
            {
                "forward": example,
                "embed": (first["input_ids"],),
                "from_embeddings": (embeddings, first["attention_mask"]),
            },
            strict=True,
        )
        traced.save(str(directory / "model.pt"))
        loaded = cast(Callable[..., Any], torch.jit.load)(
            str(directory / "model.pt"), map_location="cpu"
        ).eval()
        errors = []
        for codes in [["int f(){return 1;}"], ["strcpy(buffer,input);", "safe()"]]:
            batch = tokenizer(
                codes,
                max_length=max_length,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )
            inputs = (batch["input_ids"], batch["attention_mask"])
            expected = wrapper(*inputs)
            actual = loaded(*inputs)
            error = float(torch.max(torch.abs(expected - actual)).item())
            errors.append(error)
            if not torch.allclose(expected, actual, atol=tolerance, rtol=tolerance):
                raise ValueError("TorchScript/PyTorch numerical parity failed")
    return {"max_absolute_logit_error": max(errors), "tolerance": tolerance}
