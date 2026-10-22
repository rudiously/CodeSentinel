from pathlib import Path

from fastapi.testclient import TestClient

from model_service.app.main import app

client = TestClient(app)


def test_stub_explicit_and_deterministic() -> None:
    body = {"code": "eval(input())", "language": "python"}
    result = client.post("/predict", json=body)
    assert result.status_code == 200
    assert result.json()["artifact_kind"] == "STUB"
    assert result.json()["probability"] == 0.9
    assert result.json() == client.post("/predict", json=body).json()
    assert client.get("/health").json()["model_mode"] == "stub"


def test_limits_and_batch_order() -> None:
    assert client.post("/predict", json={"code": ""}).status_code == 422
    assert client.post("/predict", json={"code": "x" * 100001}).status_code == 422
    assert client.post("/predict_batch", json={"codes": ["x"] * 33}).status_code == 422
    response = client.post("/predict_batch", json={"codes": ["safe", "strcpy(a,b)"]})
    assert [p["probability"] for p in response.json()["predictions"]] == [0.1, 0.9]


def test_configured_limits_and_uniform_errors(tmp_path: "Path") -> None:
    from model_service.app.main import create_app
    from model_service.app.settings import Settings

    bounded = TestClient(
        create_app(
            Settings(
                max_code_chars=3,
                max_batch_size=1,
                max_request_bytes=100,
                model_artifact_dir=tmp_path / "missing",
            )
        )
    )
    for endpoint, body in [
        ("/predict", {"code": "long"}),
        ("/predict_batch", {"codes": ["x", "y"]}),
        ("/predict_batch", {"codes": [""]}),
    ]:
        result = bounded.post(endpoint, json=body)
        assert result.status_code == 422
        assert set(result.json()["error"]) == {"code", "message", "request_id"}
    assert bounded.post("/predict", content=b"x" * 101).status_code == 413
    assert bounded.get("/no-such-route").json()["error"]["code"] == "HTTP_ERROR"


def test_artifact_does_not_silently_fall_back(tmp_path: "Path") -> None:
    from model_service.app.main import create_app
    from model_service.app.settings import Settings

    (tmp_path / "model.onnx").write_bytes(b"invalid")
    unavailable = TestClient(create_app(Settings(model_artifact_dir=tmp_path)))
    assert unavailable.get("/health").status_code == 503
    assert unavailable.post("/predict", json={"code": "safe"}).status_code == 503


def test_metrics_record_errors_and_inference() -> None:
    client.post("/predict", json={"code": "safe"})
    client.post("/predict", json={"code": ""})
    text = client.get("/metrics").text
    assert "codesentinel_model_inference_seconds_count" in text
    assert "codesentinel_model_errors_total" in text
