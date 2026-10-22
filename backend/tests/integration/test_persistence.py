import json
from pathlib import Path
import subprocess
import os
import sys

from sqlalchemy import inspect, text

from backend.app.db.models import Base
from backend.app.db.repositories import ScanStore
from backend.app.db.session import make_engine
from shared.schemas import ScanReport


def test_persistence_strips_source_and_tokens() -> None:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    store = ScanStore(engine)
    report = ScanReport.model_validate_json(
        Path("fixtures/scan_report.json").read_text()
    )
    store.save(report)
    saved = store.get(str(report.scan_id))
    assert saved is not None
    assert saved["functions"][0]["code"] == ""
    assert saved["functions"][0]["token_importance"] == []
    assert "return a + b" not in json.dumps(saved)
    assert store.repos()[0]["repository"] == "demo/example"
    assert store.repos()[0]["latest_scan"] is not None
    assert len(store.history(decision="PASS")) == 1
    assert store.history(decision="BLOCK") == []
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM scan_functions")) == 1
    engine.dispose()


def test_alembic_upgrade_downgrade(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    env = {**os.environ, "DATABASE_URL": url}
    command = [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini"]
    result = subprocess.run(
        command + ["upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    engine = make_engine(url)
    assert {"users", "repos", "scans", "scan_functions", "findings"} <= set(
        inspect(engine).get_table_names()
    )
    engine.dispose()
    result = subprocess.run(
        command + ["downgrade", "base"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_demo_seed_is_explicitly_synthetic(tmp_path: Path) -> None:
    from examples.seed_demo_data import seed

    url = f"sqlite:///{tmp_path/'seed.db'}"
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    seed(url)
    reports = ScanStore(engine).history()
    assert len(reports) == 3
    assert all(
        report["synthetic"] and report["artifact_kind"] == "STUB" for report in reports
    )
    assert {report["decision"] for report in reports} == {"PASS", "WARN", "BLOCK"}
    engine.dispose()
