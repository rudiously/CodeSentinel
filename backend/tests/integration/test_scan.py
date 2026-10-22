import json
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.main import create_app as original_create_app
from backend.app.db.models import Base


from backend.app.services.model_client import ModelClient
from backend.app.settings import Settings
from model_service.stub_model import predict
from shared.schemas import ScanReport


def create_app(
    settings: Settings | None = None, model_client: ModelClient | None = None
) -> FastAPI:
    settings = settings or Settings()
    settings = settings.model_copy(
        update={"database_url": "sqlite:///:memory:", "auth_required": False}
    )
    app = original_create_app(settings, model_client)
    Base.metadata.create_all(app.state.store.engine)
    return app


def model_handler(request: httpx.Request) -> httpx.Response:
    data = json.loads(request.content)
    return httpx.Response(200, json=predict(data["code"], data["language"]))


def test_clean_and_vulnerable_contract_b() -> None:
    model = ModelClient("http://model", transport=httpx.MockTransport(model_handler))
    with TestClient(
        create_app(
            Settings(allow_python_ast=True, static_analysis_mode="builtin-python"),
            model,
        )
    ) as client:
        for path, expected in [
            ("examples/clean/add.py", "PASS"),
            ("examples/vulnerable/eval_input.py", "BLOCK"),
        ]:
            result = client.post(
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
            assert result.status_code == 200, result.text
            report = ScanReport.model_validate(result.json())
            assert report.decision == expected
            assert report.model_mode == "stub" and report.artifact_kind == "STUB"
            assert report.analysis.static_analyzer_mode == "builtin-python"
            if expected == "BLOCK":
                assert report.findings[0].line == 3


def test_model_failure_never_passes_scan() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with TestClient(
        create_app(
            Settings(allow_python_ast=True, static_analysis_mode="builtin-python"),
            ModelClient("http://model", transport=httpx.MockTransport(down)),
        )
    ) as client:
        response = client.post(
            "/scan",
            json={
                "files": [
                    {
                        "path": "a.py",
                        "language": "python",
                        "code": "def f():\n    return 1\n",
                    }
                ]
            },
        )
        assert response.status_code == 503
        report = ScanReport.model_validate(response.json())
        assert report.decision == "ERROR" and report.risk_score is None
        assert "MODEL_UNAVAILABLE" in report.errors[0]


def test_diff_requires_complete_source_and_filters_functions() -> None:
    with TestClient(
        create_app(
            Settings(allow_python_ast=True, static_analysis_mode="builtin-python"),
            ModelClient("http://model", transport=httpx.MockTransport(model_handler)),
        )
    ) as client:
        body = {
            "files": [
                {
                    "path": "a.py",
                    "language": "python",
                    "code": "def f():\n    return 1\n\ndef g():\n    return 2\n",
                }
            ],
            "diff": "--- a/a.py\n+++ b/a.py\n@@ -2 +2 @@\n-    return 0\n+    return 1\n",
        }
        result = client.post("/scan", json=body)
        assert result.status_code == 200
        assert [f["name"] for f in result.json()["functions"]] == ["f"]
        body["diff"] = "--- a/missing.py\n+++ b/missing.py\n@@ -1 +1 @@\n-a\n+b\n"
        assert client.post("/scan", json=body).status_code == 422


def test_file_and_function_caps_reject_before_inference() -> None:
    calls: list[str] = []

    def counted(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return model_handler(request)

    config = Settings(
        allow_python_ast=True,
        static_analysis_mode="builtin-python",
        max_files=1,
        max_functions=1,
    )
    with TestClient(
        create_app(
            config, ModelClient("http://model", transport=httpx.MockTransport(counted))
        )
    ) as client:
        source = {
            "path": "a.py",
            "language": "python",
            "code": "def f():\n return 1\ndef g():\n return 2\n",
        }
        assert client.post("/scan", json={"files": [source]}).status_code == 413
        assert (
            client.post(
                "/scan", json={"files": [source, {**source, "path": "b.py"}]}
            ).status_code
            == 413
        )
        assert calls == []


def test_scan_combines_signals_across_different_functions() -> None:
    def separate_signals(request: httpx.Request) -> httpx.Response:
        source = json.loads(request.content)["code"]
        result = predict("safe")
        if "def strong_model" in source:
            result["probability"] = 0.9
            result["label"] = "VULNERABLE"
        return httpx.Response(200, json=result)

    with TestClient(
        create_app(
            Settings(allow_python_ast=True, static_analysis_mode="builtin-python"),
            ModelClient(
                "http://model", transport=httpx.MockTransport(separate_signals)
            ),
        )
    ) as client:
        result = client.post(
            "/scan",
            json={
                "files": [
                    {
                        "path": "signals.py",
                        "language": "python",
                        "code": "def strong_model():\n    return 1\n\ndef static_finding():\n    password = 'synthetic-test-value'\n    return password\n",
                    }
                ]
            },
        )
        report = ScanReport.model_validate(result.json())
        assert result.status_code == 200
        assert all(function.decision == "WARN" for function in report.functions)
        assert report.decision == "BLOCK"
        assert abs((report.risk_score or 0) - 0.85) < 1e-9
        assert "strong_model" in report.reasons[0]


def test_outside_static_finding_obeys_combined_weights() -> None:
    with TestClient(
        create_app(
            Settings(allow_python_ast=True, static_analysis_mode="builtin-python"),
            ModelClient("http://model", transport=httpx.MockTransport(model_handler)),
        )
    ) as client:
        result = client.post(
            "/scan",
            json={
                "files": [
                    {
                        "path": "module.py",
                        "language": "python",
                        "code": "eval('synthetic-demo')\n\ndef clean():\n    return 1\n",
                    }
                ]
            },
        )
        report = ScanReport.model_validate(result.json())
        assert result.status_code == 200
        assert report.decision == "WARN"
        assert abs((report.risk_score or 0) - 0.55) < 1e-9
