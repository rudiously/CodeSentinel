"""Validated model HTTP boundary; never replace an unavailable model with a stub."""

from typing import Any

import httpx
from pydantic import ValidationError

from shared.http import ServiceError
from shared.schemas import Language, Prediction


class ModelClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
            trust_env=False,
        )

    def close(self) -> None:
        self.client.close()

    def _request(
        self, method: str, path: str, body: dict[str, object] | None = None
    ) -> Any:
        for attempt in range(2):
            try:
                response = self.client.request(method, path, json=body)
                response.raise_for_status()
                return response.json()
            except httpx.ConnectError:
                if attempt == 0:
                    continue
                raise ServiceError(
                    "MODEL_UNAVAILABLE", "Model service connection failed"
                ) from None
            except (httpx.HTTPError, ValueError):
                raise ServiceError(
                    "MODEL_UNAVAILABLE", "Model service failed or returned invalid JSON"
                ) from None
        raise ServiceError("MODEL_UNAVAILABLE", "Model request failed")

    def predict(self, code: str, language: Language) -> Prediction:
        try:
            return Prediction.model_validate(
                self._request("POST", "/predict", {"code": code, "language": language})
            )
        except ValidationError:
            raise ServiceError(
                "MODEL_INVALID_RESPONSE", "Model response violates Contract A"
            ) from None

    def predict_batch(self, codes: list[str], language: Language) -> list[Prediction]:
        data = self._request(
            "POST", "/predict_batch", {"codes": codes, "language": language}
        )
        try:
            predictions = [
                Prediction.model_validate(item) for item in data["predictions"]
            ]
            if len(predictions) != len(codes):
                raise ValueError("Batch length mismatch")
            return predictions
        except (ValidationError, KeyError, TypeError, ValueError):
            raise ServiceError(
                "MODEL_INVALID_RESPONSE", "Invalid model batch response"
            ) from None

    def info(self) -> dict[str, Any]:
        data = self._request("GET", "/model/info")
        if not isinstance(data, dict) or data.get("model_mode") not in {"stub", "real"}:
            raise ServiceError("MODEL_INVALID_RESPONSE", "Invalid model metadata")
        return data
