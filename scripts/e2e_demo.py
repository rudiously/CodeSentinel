"""LIVE TCP full-stack gate. Fails if any required service is unreachable."""

import os
from pathlib import Path

import httpx

from shared.schemas import ScanReport


def main() -> None:
    base = os.environ.get("CODESENTINEL_API_URL", "http://127.0.0.1:8000")
    token = os.environ.get("CODESENTINEL_API_TOKEN", "")
    with httpx.Client(timeout=60, follow_redirects=False, trust_env=False) as client:
        health = client.get(base + "/health")
        health.raise_for_status()
        if not token:
            login = client.post(base + "/auth/dev")
            login.raise_for_status()
            token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        ids = []
        for file in ["examples/clean/add.py", "examples/vulnerable/eval_input.py"]:
            response = client.post(
                base + "/scan",
                headers=headers,
                json={
                    "files": [
                        {
                            "path": file,
                            "language": "python",
                            "code": Path(file).read_text(),
                        }
                    ]
                },
            )
            response.raise_for_status()
            report = ScanReport.model_validate(response.json())
            ids.append(str(report.scan_id))
            assert report.decision != "ERROR"
            if health.json()["model_mode"] == "stub":
                assert report.decision == ("PASS" if "clean" in file else "BLOCK")
            print(f"LIVE {report.artifact_kind}: {file}: {report.decision}")
        history = client.get(base + "/history", headers=headers)
        history.raise_for_status()
        assert set(ids) <= {scan["scan_id"] for scan in history.json()}
        assert "codesentinel_scans_total" in client.get(base + "/metrics").text
        for url in [
            "http://127.0.0.1:3002/",
            "http://127.0.0.1:9090/-/healthy",
            "http://127.0.0.1:3001/api/health",
            "http://127.0.0.1:5001/health",
        ]:
            client.get(url).raise_for_status()
        targets = client.get("http://127.0.0.1:9090/api/v1/targets")
        targets.raise_for_status()
        assert all(
            target["health"] == "up"
            for target in targets.json()["data"]["activeTargets"]
        )
    print(
        "LIVE full-stack e2e passed; browser interaction is a separate frontend check."
    )


if __name__ == "__main__":
    main()
