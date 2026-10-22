from typing import Any

from sqlalchemy import Engine, desc, select
from sqlalchemy.orm import Session

from backend.app.db.models import FindingRow, Repo, Scan, ScanFunction
from shared.schemas import ScanReport


class ScanStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save(self, report: ScanReport) -> None:
        data = report.model_dump(mode="json")
        # Strip source AND attribution token text: both can contain proprietary code.
        for function in data["functions"]:
            function["code"] = ""
            function["token_importance"] = []
        owner, name = report.repository.split("/", 1)
        with Session(self.engine) as session, session.begin():
            repo = session.scalar(
                select(Repo).where(Repo.owner == owner, Repo.name == name)
            )
            if repo is None:
                repo = Repo(owner=owner, name=name)
                session.add(repo)
                session.flush()
            session.add(
                Scan(
                    id=str(report.scan_id),
                    repo_id=repo.id,
                    timestamp=report.timestamp,
                    decision=report.decision,
                    risk_score=report.risk_score,
                    model_version=report.model_version,
                    model_mode=report.model_mode,
                    artifact_kind=report.artifact_kind,
                    synthetic=report.synthetic,
                    reasons=report.reasons,
                    report=data,
                )
            )
            session.flush()
            for function in report.functions:
                session.add(
                    ScanFunction(
                        scan_id=str(report.scan_id),
                        name=function.name,
                        file=function.file,
                        start_line=function.start_line,
                        end_line=function.end_line,
                        probability=function.probability,
                        risk_score=function.risk_score,
                        decision=function.decision,
                    )
                )
            for finding in report.findings:
                session.add(
                    FindingRow(
                        scan_id=str(report.scan_id),
                        file=finding.file,
                        rule=finding.rule,
                        severity=finding.severity,
                        line=finding.line,
                        message=finding.message,
                    )
                )

    def history(
        self,
        repository: str | None = None,
        decision: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        statement = select(Scan).join(Repo)
        if repository:
            owner, name = repository.split("/", 1)
            statement = statement.where(Repo.owner == owner, Repo.name == name)
        if decision:
            statement = statement.where(Scan.decision == decision)
        with Session(self.engine) as session:
            return [
                scan.report
                for scan in session.scalars(
                    statement.order_by(desc(Scan.timestamp)).limit(limit).offset(offset)
                )
            ]

    def get(self, scan_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            scan = session.get(Scan, scan_id)
            return scan.report if scan else None

    def repos(self) -> list[dict[str, object]]:
        with Session(self.engine) as session:
            result: list[dict[str, object]] = []
            for repo in session.scalars(select(Repo).order_by(Repo.owner, Repo.name)):
                latest = session.scalar(
                    select(Scan)
                    .where(Scan.repo_id == repo.id)
                    .order_by(desc(Scan.timestamp))
                    .limit(1)
                )
                summary = (
                    {
                        "decision": latest.decision,
                        "risk_score": latest.risk_score,
                        "artifact_kind": latest.artifact_kind,
                        "timestamp": latest.timestamp.isoformat(),
                    }
                    if latest
                    else None
                )
                result.append(
                    {
                        "id": repo.id,
                        "repository": f"{repo.owner}/{repo.name}",
                        "latest_scan": summary,
                    }
                )
            return result
