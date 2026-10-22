from sqlalchemy import Engine, create_engine, event
from sqlalchemy.pool import StaticPool


def make_engine(url: str) -> Engine:
    options: dict[str, object] = {}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def foreign_keys(connection: object, record: object) -> None:
            from typing import Any, cast

            cast(Any, connection).execute("PRAGMA foreign_keys=ON")

    return engine
