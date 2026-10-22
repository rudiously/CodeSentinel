"""Primary Action path: complete file blobs -> /scan -> comment -> exit decision."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

import httpx

from shared.schemas import ScanReport


def exit_code(report: ScanReport) -> int:
    return {"PASS": 0, "WARN": 0, "BLOCK": 1, "ERROR": 2}[report.decision]


def collect_files(base: str, head: str, max_files: int = 50) -> list[dict[str, str]]:
    if not all(re.fullmatch(r"[a-fA-F0-9]{40,64}", sha) for sha in (base, head)):
        raise ValueError("Expected full base/head Git SHAs")
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "-z", base, head, "--"],
        capture_output=True,
        check=True,
        timeout=30,
    )
    paths = [p.decode("utf-8") for p in result.stdout.split(b"\0") if p]
    if len(paths) > max_files:
        raise ValueError("PR exceeds file limit")
    files = []
    for path in paths:
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
            raise ValueError("Unsupported changed file; manual review required")
        content = subprocess.run(
            ["git", "show", f"{head}:{path}"],
            capture_output=True,
            check=True,
            timeout=30,
        ).stdout
        if len(content) > 100000:
            raise ValueError("Source file exceeds byte limit")
        files.append(
            {"path": path, "language": language, "code": content.decode("utf-8")}
        )
    if not files:
        raise ValueError("No supported changed files; cannot silently PASS")
    return files


def scan_and_comment(
    client: httpx.Client,
    api_url: str,
    repository: str,
    number: int,
    payload: dict[str, Any],
    github_token: str,
    api_token: str,
) -> ScanReport:
    if (
        not re.fullmatch(
            r"[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*", repository
        )
        or number <= 0
    ):
        raise ValueError("Invalid PR identity")
    parsed = httpx.URL(api_url)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.userinfo
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Invalid configured API URL")
    if parsed.scheme == "http" and parsed.host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Remote API must use HTTPS")
    response = client.post(
        api_url.rstrip("/") + "/scan",
        json=payload,
        headers={"Authorization": f"Bearer {api_token}"} if api_token else {},
    )
    if response.status_code not in {200, 503}:
        response.raise_for_status()
    report = ScanReport.model_validate(response.json())
    comment = f"<!-- codesentinel -->\nCodeSentinel: **{report.decision}**\nModel: **{report.model_mode.upper()} / {report.artifact_kind}**\nRisk: {report.risk_score}\nFindings: {len(report.findings)}\nScan: {report.scan_id}\n\nSignals do not guarantee safety."
    posted = client.post(
        f"https://api.github.com/repos/{repository}/issues/{number}/comments",
        json={"body": comment},
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    posted.raise_for_status()
    return report


def workload_token(client: httpx.Client) -> str:
    url = httpx.URL(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"])
    if url.scheme != "https" or not url.host.endswith(".actions.githubusercontent.com"):
        raise ValueError("Unexpected Actions identity endpoint")
    response = client.get(
        url.copy_merge_params(
            {"audience": os.environ.get("CODESENTINEL_OIDC_AUDIENCE", "codesentinel")}
        ),
        headers={
            "Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
        },
    )
    response.raise_for_status()
    return str(response.json()["value"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.dry_run:
        if not args.report:
            parser.error("--dry-run requires --report")
        report = ScanReport.model_validate_json(args.report.read_text())
    else:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        repository = event["repository"]["full_name"]
        pr = event["pull_request"]
        files = collect_files(pr["base"]["sha"], pr["head"]["sha"])
        with httpx.Client(
            timeout=60, follow_redirects=False, trust_env=False
        ) as client:
            report = scan_and_comment(
                client,
                os.environ["CODESENTINEL_API_URL"],
                repository,
                event["number"],
                {"repository": repository, "files": files},
                os.environ["GITHUB_TOKEN"],
                os.environ.get("CODESENTINEL_API_TOKEN") or workload_token(client),
            )
    print(
        f"CodeSentinel {report.decision} ({report.model_mode.upper()}/{report.artifact_kind})"
    )
    return exit_code(report)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, httpx.HTTPError):
        print("CodeSentinel ERROR: request or gate failed; source and tokens omitted.")
        raise SystemExit(2)
