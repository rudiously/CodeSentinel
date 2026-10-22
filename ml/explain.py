"""Integrated gradients: local sensitivity, not causal vulnerability evidence."""

from collections.abc import Callable

import torch


def integrated_gradients(
    forward: Callable[[torch.Tensor], torch.Tensor],
    inputs: torch.Tensor,
    baseline: torch.Tensor | None = None,
    steps: int = 32,
) -> torch.Tensor:
    if steps < 2:
        raise ValueError("At least two integration steps required")
    reference = torch.zeros_like(inputs) if baseline is None else baseline
    if reference.shape != inputs.shape:
        raise ValueError("Baseline shape must match inputs")
    delta = inputs.detach() - reference.detach()
    gradients = []
    for index in range(steps):
        point = (
            (reference + (index + 0.5) / steps * delta).detach().requires_grad_(True)
        )
        score = forward(point)
        gradient = torch.autograd.grad(score.sum(), point)[0]
        gradients.append(gradient.detach())
    return delta * torch.stack(gradients).mean(dim=0)


def map_to_lines(
    code: str, offsets: list[tuple[int, int]], importance: list[float]
) -> dict[int, float]:
    if len(offsets) != len(importance):
        raise ValueError("Offsets and attributions must align")
    lines: dict[int, float] = {}
    for (start, end), value in zip(offsets, importance, strict=True):
        if start < 0 or end < start or end > len(code):
            raise ValueError("Token offsets outside source")
        if start == end:
            continue
        for position in range(start, end):
            line = code.count("\n", 0, position) + 1
            lines[line] = lines.get(line, 0) + value / (end - start)
    return lines
