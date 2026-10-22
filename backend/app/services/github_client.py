"""GitHub API access is pinned to a fixed origin; payload URLs are never fetched."""

import base64
import re
from time import time
from typing import Any

import httpx
import jwt

from backend.app.schemas import ScanRequest
from shared.http import ServiceError
from shared.schemas import ScanReport


class GitHubClient:
    def __init__(
        self,
        token: str,
        transport: httpx.BaseTransport | None = None,
        app_id: str = "",
        installation_id: int = 0,
        private_key: str = "",
    ) -> None:
        self.token = token
        self.app_id, self.installation_id, self.private_key = (
            app_id,
            installation_id,
            private_key,
        )
        self.token_expiry = 0.0
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    def close(self) -> None:
        self.client.close()

    def request(
        self, method: str, path: str, body: dict[str, object] | None = None
    ) -> Any:
        if (
            (not self.token or (self.token_expiry and time() >= self.token_expiry))
            and self.app_id
            and self.installation_id
            and self.private_key
        ):
            self._installation_token()
        if not self.token:
            raise ServiceError(
                "GITHUB_NOT_CONFIGURED", "GitHub credentials are missing"
            )
        if (
            not path.startswith("/repos/")
            or ":" in path
            or ".." in path
            or "\\" in path
        ):
            raise ServiceError("INVALID_GITHUB_PATH", "GitHub path not allowed", 422)
        try:
            response = self.client.request(
                method,
                path,
                json=body,
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise ServiceError("GITHUB_ERROR", "GitHub API request failed") from None

    def _installation_token(self) -> None:
        now = int(time())
        try:
            signed = jwt.encode(
                {"iat": now - 30, "exp": now + 540, "iss": self.app_id},
                self.private_key.replace("\\n", "\n"),
                algorithm="RS256",
            )
            response = self.client.post(
                f"/app/installations/{self.installation_id}/access_tokens",
                headers={"Authorization": f"Bearer {signed}"},
            )
            response.raise_for_status()
            self.token = response.json()["token"]
            self.token_expiry = time() + 3000
        except (httpx.HTTPError, ValueError, KeyError, jwt.PyJWTError):
            raise ServiceError(
                "GITHUB_AUTH_FAILED", "Could not obtain GitHub App installation token"
            ) from None

    @staticmethod
    def repository_path(repository: str) -> str:
        if (
            not re.fullmatch(
                r"[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*", repository
            )
            or ".." in repository
        ):
            raise ServiceError(
                "INVALID_REPOSITORY", "Invalid repository identifier", 422
            )
        return f"/repos/{repository}"

    def collect(
        self, repository: str, number: int, max_files: int = 50, max_bytes: int = 100000
    ) -> ScanRequest:
        base = self.repository_path(repository)
        if number <= 0:
            raise ServiceError("INVALID_PR", "Invalid pull request number", 422)
        entries = self.request("GET", f"{base}/pulls/{number}/files?per_page=100")
        if not isinstance(entries, list) or len(entries) > max_files:
            raise ServiceError("TOO_MANY_FILES", "PR exceeds file limit", 413)
        files = []
        for entry in entries:
            if entry["status"] == "removed":
                continue
            path = entry["filename"]
            extension = path.rsplit(".", 1)[-1].lower()
            language = {
                "py": "python",
                "c": "c",
                "h": "c",
                "cpp": "cpp",
                "cc": "cpp",
                "hpp": "cpp",
            }.get(extension)
            if language is None:
                raise ServiceError(
                    "UNSUPPORTED_LANGUAGE",
                    "PR includes an unsupported file; review manually",
                    422,
                )
            sha = entry["sha"]
            if not re.fullmatch(r"[a-fA-F0-9]{40,64}", sha):
                raise ServiceError("INVALID_BLOB", "Invalid Git blob identifier", 422)
            blob = self.request("GET", f"{base}/git/blobs/{sha}")
            if (
                blob.get("encoding") != "base64"
                or blob.get("size", max_bytes + 1) > max_bytes
            ):
                raise ServiceError(
                    "BLOB_TOO_LARGE", "Source blob too large or unsupported", 413
                )
            try:
                code = base64.b64decode(blob["content"], validate=False).decode("utf-8")
            except (ValueError, UnicodeError, KeyError):
                raise ServiceError(
                    "INVALID_BLOB", "GitHub source blob is invalid", 422
                ) from None
            if len(code.encode()) > max_bytes:
                raise ServiceError(
                    "BLOB_TOO_LARGE", "Decoded source exceeds byte limit", 413
                )
            files.append({"path": path, "language": language, "code": code})
        if not files:
            raise ServiceError(
                "NO_SOURCE", "No supported post-change source is available", 422
            )
        # Fetching complete blobs intentionally scans whole files, not incomplete patches.
        return ScanRequest.model_validate({"repository": repository, "files": files})

    def assert_head(self, repository: str, number: int, expected: str) -> None:
        current = self.request(
            "GET", f"{self.repository_path(repository)}/pulls/{number}"
        )
        if current.get("head", {}).get("sha") != expected:
            raise ServiceError(
                "PR_CHANGED",
                "PR head changed during processing; retry current revision",
            )

    def post_report(
        self,
        repository: str,
        number: int,
        sha: str,
        report: ScanReport,
        *,
        checks: bool = True,
    ) -> None:
        base = self.repository_path(repository)
        if number <= 0 or not re.fullmatch(r"[a-fA-F0-9]{40,64}", sha):
            raise ServiceError("INVALID_PR", "Invalid pull request identity", 422)
        body = f"<!-- codesentinel -->\n## CodeSentinel: {report.decision}\nModel: {report.model_mode.upper()} / {report.artifact_kind}\nRisk: {report.risk_score if report.risk_score is not None else 'unavailable'}\nFindings: {len(report.findings)}\nScan: {report.scan_id}\n\nAutomated signals do not guarantee code safety."
        self.request("POST", f"{base}/issues/{number}/comments", {"body": body})
        if checks:
            self.request(
                "POST",
                f"{base}/check-runs",
                {
                    "name": "CodeSentinel",
                    "head_sha": sha,
                    "status": "completed",
                    "conclusion": (
                        "failure"
                        if report.decision in {"BLOCK", "ERROR"}
                        else "success"
                    ),
                    "output": {
                        "title": f"CodeSentinel {report.decision}",
                        "summary": body,
                    },
                },
            )
