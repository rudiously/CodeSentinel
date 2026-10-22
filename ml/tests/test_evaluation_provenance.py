from pathlib import Path
import json

import pytest

from ml.evaluation_run import evaluation_provenance, run


def test_trained_artifact_on_synthetic_data_is_not_research_evidence() -> None:
    synthetic, claim = evaluation_provenance(
        {"artifact_kind": "TRAINED", "synthetic": False}, [{"synthetic": True}]
    )
    assert synthetic and claim == "SYNTHETIC PIPELINE VERIFICATION ONLY"
    synthetic, claim = evaluation_provenance({"artifact_kind": "SMOKE"}, [{}])
    assert synthetic and claim == "SMOKE PIPELINE VERIFICATION ONLY"


def test_validation_leakage_rejected_before_artifact_load(tmp_path: Path) -> None:
    data = tmp_path / "records.jsonl"
    data.write_text(json.dumps({"code": "int f(){return 1;}", "label": 0}) + "\n")
    with pytest.raises(ValueError, match="overlap"):
        run(
            tmp_path / "nonexistent-artifact",
            data,
            tmp_path / "output.json",
            validation_file=data,
        )
    assert not (tmp_path / "output.json").exists()
