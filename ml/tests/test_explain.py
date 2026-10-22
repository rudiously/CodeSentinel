import pytest
import torch

from ml.explain import integrated_gradients, map_to_lines


def test_integrated_gradients_linear_completeness() -> None:
    value = torch.tensor([[1.0, 2.0]])
    weights = torch.tensor([[3.0, -1.0]])
    attribution = integrated_gradients(
        lambda x: (x * weights).sum(dim=-1), value, steps=8
    )
    assert torch.allclose(attribution, torch.tensor([[3.0, -2.0]]))
    assert attribution.sum().item() == pytest.approx(1.0)


def test_offset_line_mapping_spans_newline() -> None:
    mapped = map_to_lines("ab\ncd", [(0, 2), (2, 5)], [0.4, 0.6])
    assert sum(mapped.values()) == pytest.approx(1.0)
    assert mapped[1] == pytest.approx(0.6)
    assert mapped[2] == pytest.approx(0.4)
