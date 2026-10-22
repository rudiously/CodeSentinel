from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[str] = mapped_column(String(100), unique=True)
    login: Mapped[str] = mapped_column(String(200))


class Repo(Base):
    __tablename__ = "repos"
    __table_args__ = (UniqueConstraint("owner", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repos.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    decision: Mapped[str] = mapped_column(String(10), index=True)
    risk_score: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(200))
    model_mode: Mapped[str] = mapped_column(String(20))
    artifact_kind: Mapped[str] = mapped_column(String(20))
    synthetic: Mapped[bool]
    reasons: Mapped[list[str]] = mapped_column(JSON)
    report: Mapped[dict[str, Any]] = mapped_column(JSON)


class ScanFunction(Base):
    __tablename__ = "scan_functions"
    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(500))
    file: Mapped[str] = mapped_column(String(500))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    probability: Mapped[float | None] = mapped_column(Float)
    risk_score: Mapped[float | None] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String(10))


class FindingRow(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True
    )
    function_id: Mapped[int | None] = mapped_column(ForeignKey("scan_functions.id"))
    file: Mapped[str] = mapped_column(String(500))
    rule: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(10))
    line: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(String(2000))
