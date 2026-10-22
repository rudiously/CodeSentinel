import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from shared.schemas import Prediction, ScanReport


def test_shared_fixtures() -> None:
    Prediction.model_validate_json(Path("fixtures/prediction.json").read_text())
    report = ScanReport.model_validate_json(
        Path("fixtures/scan_report.json").read_text()
    )
    assert report.synthetic and report.artifact_kind == "STUB"


@pytest.mark.parametrize("probability", [-1, 1.1, float("nan"), float("inf")])
def test_invalid_probability(probability: float) -> None:
    data = json.loads(Path("fixtures/prediction.json").read_text())
    data["probability"] = probability
    with pytest.raises(ValidationError):
        Prediction.model_validate(data)


def test_provenance_and_error_invariants() -> None:
    data = json.loads(Path("fixtures/scan_report.json").read_text())
    data["errors"] = ["model unavailable"]
    with pytest.raises(ValidationError):
        ScanReport.model_validate(data)
    data["errors"] = []
    data["artifact_kind"] = "TRAINED"
    with pytest.raises(ValidationError):
        ScanReport.model_validate(data)
