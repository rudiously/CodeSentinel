"""Seed explicitly SYNTHETIC reports; never fabricate real scan or ML results."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.app.db.repositories import ScanStore
from backend.app.db.session import make_engine
from shared.schemas import ScanReport


def seed(url: str) -> None:
    engine = make_engine(url)
    store = ScanStore(engine)
    sample = ScanReport.model_validate_json(
        Path("fixtures/scan_report.json").read_text()
    )
    for decision, risk in [("PASS", 0.05), ("WARN", 0.5), ("BLOCK", 0.9)]:
        data = sample.model_dump(mode="json")
        data.update(
            scan_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision=decision,
            risk_score=risk,
            synthetic=True,
            reasons=["SYNTHETIC demonstration record; not a measured scan"],
        )
        data["functions"][0].update(decision=decision, risk_score=risk)
        store.save(ScanReport.model_validate(data))
    engine.dispose()
    print("Seeded 3 SYNTHETIC STUB records; not real model results.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    seed(parser.parse_args().database_url)
