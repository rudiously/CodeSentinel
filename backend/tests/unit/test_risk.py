import pytest

from backend.app.services.risk_engine import RiskConfig, score_risk
from shared.schemas import Finding, Mode


def finding(severity: str) -> Finding:
    return Finding.model_validate(
        {
            "file": "a.py",
            "rule": "test-rule",
            "severity": severity,
            "line": 2,
            "message": "Test finding",
        }
    )


@pytest.mark.parametrize(
    "probability,expected",
    [
        (0.0, "PASS"),
        (0.349999, "PASS"),
        (0.35, "WARN"),
        (0.649999, "WARN"),
        (0.65, "BLOCK"),
        (1.0, "BLOCK"),
    ],
)
def test_thresholds(probability: float, expected: str) -> None:
    result = score_risk(probability, [], "example", "model_only")
    assert result.decision == expected
    assert result.risk_score == probability


@pytest.mark.parametrize(
    "severity,static", [("Low", 0.3), ("Medium", 0.6), ("High", 1.0)]
)
def test_static_severity_and_combination(severity: str, static: float) -> None:
    result = score_risk(0.8, [finding(severity)], "example")
    expected = min(1.0, 0.4 + 0.5 * static + (0.1 if static >= 0.6 else 0))
    assert result.risk_score == pytest.approx(expected)
    assert "test-rule" in " ".join(result.reasons)


def test_high_safety_rule_with_model_only() -> None:
    result = score_risk(0, [finding("High")], "example", "model_only")
    assert result.decision == "WARN" and result.risk_score == 0


def test_maximum_not_sum_and_agreement_boundary() -> None:
    findings = [finding("Low"), finding("Medium")]
    assert score_risk(0.5, findings, "example").risk_score == pytest.approx(0.65)
    assert score_risk(0.499, findings, "example").risk_score == pytest.approx(0.5495)


@pytest.mark.parametrize("mode", ["combined", "model_only"])
def test_model_down_never_pass(mode: Mode) -> None:
    result = score_risk(None, [], "example", mode)
    assert result.decision == "ERROR" and result.risk_score is None


def test_static_only_does_not_require_model() -> None:
    assert (
        score_risk(None, [finding("Medium")], "example", "static_only").risk_score
        == 0.6
    )
    assert (
        score_risk(0.1, [], "example", analysis_error="scanner down").decision
        == "ERROR"
    )


@pytest.mark.parametrize("probability", [-1, 1.1, float("nan"), float("inf")])
def test_invalid_model_inputs(probability: float) -> None:
    with pytest.raises(ValueError):
        score_risk(probability, [], "example")


def test_configuration_validation() -> None:
    with pytest.raises(ValueError):
        RiskConfig(model_weight=0.9)
    with pytest.raises(ValueError):
        RiskConfig(warn_threshold=0.8, block_threshold=0.6)
    assert (
        score_risk(0.5, [], "example", config=RiskConfig(warn_threshold=0.2)).decision
        == "WARN"
    )
