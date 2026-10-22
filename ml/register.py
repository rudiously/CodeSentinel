"""Artifact manifests include hashes, calibration, dataset identity and git revision."""

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    # Refuse an ancestor repository: it does not identify this project snapshot.
    if not Path(".git").exists():
        return "UNAVAILABLE: workspace git initialization denied"
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE: no commit"


def write_metadata(directory: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    files = {
        str(path.relative_to(directory)): sha256(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name != "metadata.json"
    }
    result = {
        **metadata,
        "files_sha256": files,
        "weights_sha256": sha256(directory / "model.pt"),
        "format": "torchscript",
        "model_file": "model.pt",
        "git_commit": git_commit(),
    }
    (directory / "metadata.json").write_text(json.dumps(result, indent=2))
    return result


def register_version(run_id: str, source: str, kind: str) -> str:
    """Register a versioned raw artifact; not advertised as an MLflow pyfunc flavor."""
    from mlflow.tracking import MlflowClient
    from mlflow.exceptions import MlflowException

    client = MlflowClient()
    name = "CodeSentinel-CodeBERT-SMOKE" if kind == "SMOKE" else "CodeSentinel-CodeBERT"
    try:
        client.create_registered_model(name, tags={"artifact_kind": kind})
    except MlflowException as exc:
        if exc.error_code != "RESOURCE_ALREADY_EXISTS":
            raise
    version = client.create_model_version(
        name=name,
        source=source,
        run_id=run_id,
        tags={
            "artifact_kind": kind,
            "format": "torchscript",
            "loader": "ml.predictor.Predictor",
        },
    )
    return str(version.version)
