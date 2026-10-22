"""In-process two-service HTTP smoke test; no real model metrics are measured."""

import os
from pathlib import Path

from fastapi.testclient import TestClient
import httpx

from backend.app.db.models import Base
from backend.app.main import create_app
from backend.app.settings import Settings
from backend.app.services.model_client import ModelClient
from model_service.app.main import create_app as model_app
from shared.schemas import ScanReport


def main() -> None:
    offline = os.environ.get("CODESENTINEL_OFFLINE") == "1"
    with TestClient(model_app()) as inference:

        def forward(request: httpx.Request) -> httpx.Response:
            result = inference.request(
                request.method,
                request.url.path,
                content=request.content,
                headers={"Content-Type": "application/json"},
            )
            return httpx.Response(result.status_code, json=result.json())

        model = ModelClient(
            "http://model-service", transport=httpx.MockTransport(forward)
        )
        settings = Settings(
            auth_required=False,
            allow_python_ast=offline,
            static_analysis_mode="builtin-python" if offline else "external",
        )
        app = create_app(
            settings.model_copy(update={"database_url": "sqlite:///:memory:"}), model
        )
        Base.metadata.create_all(app.state.store.engine)
        with TestClient(app) as client:
            for path, expected in [
                ("examples/clean/add.py", "PASS"),
                ("examples/vulnerable/eval_input.py", "BLOCK"),
            ]:
                response = client.post(
                    "/scan",
                    json={
                        "files": [
                            {
                                "path": path,
                                "language": "python",
                                "code": Path(path).read_text(),
                            }
                        ]
                    },
                )
                report = ScanReport.model_validate(response.json())
                assert response.status_code == 200, (
                    response.status_code,
                    report.errors,
                )
                assert report.decision == expected, (path, report.decision)
                assert report.model_mode == "stub" and report.artifact_kind == "STUB"
                print(
                    f"IN-PROCESS HTTP STUB: {path}: {report.decision}; analysis={report.analysis.model_dump()}"
                )
    print(
        "SMOKE PASSED; no Docker/network transport or trained model evaluation claimed."
    )


if __name__ == "__main__":
    main()
