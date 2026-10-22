import json
from pathlib import Path

import pytest

from ml.predictor import Predictor


def test_artifact_integrity_rejected_before_loading(tmp_path: Path) -> None:
    (tmp_path / "model.pt").write_bytes(b"corrupt")
    (tmp_path / "metadata.json").write_text(
        json.dumps(
            {
                "format": "torchscript",
                "model_file": "model.pt",
                "artifact_kind": "SMOKE",
                "weights_sha256": "0" * 64,
                "files_sha256": {"model.pt": "0" * 64},
            }
        )
    )
    with pytest.raises(ValueError, match="SHA256"):
        Predictor(tmp_path)


def test_manifest_traversal_rejected(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text(
        json.dumps(
            {
                "format": "torchscript",
                "model_file": "model.pt",
                "artifact_kind": "SMOKE",
                "weights_sha256": "0" * 64,
                "files_sha256": {"model.pt": "0" * 64, "../secret": "0" * 64},
            }
        )
    )
    with pytest.raises(ValueError):
        Predictor(tmp_path)
