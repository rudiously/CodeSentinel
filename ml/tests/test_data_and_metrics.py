import pytest

from ml.calibrate import calibrate
from ml.data.clean import clean, code_hash
from ml.data.split import split_records
from ml.evaluate import evaluate


def test_clean_conflicts_and_disjoint_seeded_splits() -> None:
    data = [{"code": f"int f{i}(){{return {i};}}", "label": i % 2} for i in range(100)]
    data.extend([data[0], {"code": data[1]["code"], "label": 0}])
    cleaned, report = clean(data)
    assert report["duplicate_rows"] == 1 and report["conflicting_label_rows"] == 2
    first = split_records(cleaned, 42)
    assert first == split_records(cleaned, 42)
    hashes = [{code_hash(row["code"]) for row in items} for items in first.values()]
    assert not hashes[0] & hashes[1] and not hashes[0] & hashes[2]


def test_calibration_rejects_test_tuning() -> None:
    with pytest.raises(ValueError, match="validation"):
        calibrate([[1, 0], [0, 1]], [0, 1], split="test")
    fitted = calibrate([[2, 0], [0, 2], [1, 0], [0, 1]], [0, 1, 0, 1])
    assert fitted["temperature"] > 0 and 0 <= fitted["classification"] <= 1
    assert fitted["validation_recall"] >= 0.8


def test_measured_metrics() -> None:
    result = evaluate([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
    assert result["f1"] == 1.0 and result["confusion_matrix"] == [[2, 0], [0, 2]]


def test_decision_metrics_apply_high_severity_safety_floor() -> None:
    from backend.app.services.risk_engine import score_risk
    from ml.evaluate import evaluate_decisions
    from shared.schemas import Finding

    high = Finding(
        file="test.py",
        rule="synthetic-rule",
        severity="High",
        line=1,
        message="Synthetic regression",
    )
    result = score_risk(0.05, [high], "example", "model_only")
    assert result.decision == "WARN" and result.risk_score == 0.05
    metrics = evaluate_decisions([1, 0], [0.05, 0.1], [result.decision, "PASS"])
    assert metrics["flagged_WARN_or_BLOCK"]["recall"] == 1.0
    assert metrics["flagged_WARN_or_BLOCK"]["prediction_source"] == "decisions"
    with pytest.raises(ValueError):
        evaluate_decisions([1], [0.0], ["ERROR"])


@pytest.mark.parametrize("probability", [float("nan"), float("inf"), -0.1, 1.1])
def test_evaluation_rejects_nonfinite_and_out_of_range_scores(
    probability: float,
) -> None:
    with pytest.raises(ValueError, match="Invalid evaluation inputs"):
        evaluate([0, 1], [0.0, probability])
