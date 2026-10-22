"""Verify a locally trained SMOKE artifact through the real predictor and HTTP API."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil

from fastapi.testclient import TestClient

from ml.predictor import Predictor
from model_service.app.main import create_app
from model_service.app.settings import Settings


def verify(directory: Path) -> None:
    predictor = Predictor(directory)
    assert predictor.metadata["artifact_kind"] == "SMOKE"
    values = predictor.predict_batch(
        ["int f(){return 1;}", "void f(){strcpy(b,x);}"], "c"
    )
    assert len(values) == 2 and all(
        p.model_mode == "real" and p.artifact_kind == "SMOKE" for p in values
    )
    if predictor.metadata.get("attribution_method") == "integrated-gradients":
        assert all(value.token_importance for value in values)
        explained = predictor.predict("int f(){\n return 1;\n}")
        assert {token.line for token in explained.token_importance} == {1, 2, 3}
        assert (
            abs(
                sum(abs(token.importance) for token in explained.token_importance) - 1.0
            )
            < 1e-5
        )
    with TestClient(create_app(Settings(model_artifact_dir=directory))) as client:
        assert client.get("/health").json()["artifact_kind"] == "SMOKE"
        assert client.get("/model/info").json()["metrics"] is None
        response = client.post(
            "/predict", json={"code": "int f(){return 1;}", "language": "c"}
        )
        assert (
            response.status_code == 200 and response.json()["artifact_kind"] == "SMOKE"
        )
    with TemporaryDirectory() as temporary:
        corrupted = Path(temporary) / "artifact"
        shutil.copytree(directory, corrupted)
        with (corrupted / "model.pt").open("ab") as stream:
            stream.write(b"corrupt")
        try:
            Predictor(corrupted)
        except ValueError:
            pass
        else:
            raise AssertionError("Corrupt artifact loaded")
    print(
        "SMOKE artifact verified: batch inference, API provenance, hidden performance metrics, SHA256 rejection."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    verify(parser.parse_args().artifact)
