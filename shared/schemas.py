"""Executable Contracts A and B. Source and labels are never inferred provenance."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Language = Literal["c", "cpp", "python"]
Decision = Literal["PASS", "WARN", "BLOCK", "ERROR"]
Mode = Literal["combined", "model_only", "static_only"]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class TokenImportance(ContractModel):
    token: str
    line: int = Field(ge=1)
    importance: float = Field(allow_inf_nan=False)


class Prediction(ContractModel):
    probability: Probability
    label: Literal["SAFE", "VULNERABLE"]
    token_importance: list[TokenImportance]
    model_version: str
    model_mode: Literal["stub", "real"]
    artifact_kind: Literal["STUB", "SMOKE", "TRAINED"]

    @model_validator(mode="after")
    def provenance(self) -> "Prediction":
        if (self.model_mode == "stub") != (self.artifact_kind == "STUB"):
            raise ValueError("Inconsistent model provenance")
        return self


class Finding(ContractModel):
    file: str
    rule: str
    severity: Literal["High", "Medium", "Low"]
    line: int = Field(ge=1)
    message: str


class FunctionReport(ContractModel):
    name: str
    file: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    probability: Probability | None
    risk_score: Probability | None
    decision: Decision
    code: str
    token_importance: list[TokenImportance]

    @model_validator(mode="after")
    def valid_range(self) -> "FunctionReport":
        if self.end_line < self.start_line:
            raise ValueError("Invalid function line range")
        if (self.decision == "ERROR") != (self.risk_score is None):
            raise ValueError("ERROR requires null risk; other decisions require a risk")
        return self


class ScanAnalysis(ContractModel):
    static_analyzer_mode: str
    extractor_modes: list[str]
    ablation_mode: Mode


class ScanReport(ContractModel):
    analysis: ScanAnalysis
    scan_id: UUID
    repository: str
    decision: Decision
    risk_score: Probability | None
    functions: list[FunctionReport]
    findings: list[Finding]
    reasons: list[str]
    model_version: str
    model_mode: Literal["stub", "real", "unavailable"]
    artifact_kind: Literal["STUB", "SMOKE", "TRAINED", "UNAVAILABLE"]
    synthetic: bool
    timestamp: datetime
    errors: list[str]

    @model_validator(mode="after")
    def consistent(self) -> "ScanReport":
        if (self.decision == "ERROR") != (self.risk_score is None):
            raise ValueError("ERROR requires null risk")
        if self.errors and self.decision != "ERROR":
            raise ValueError("Analysis failures require ERROR")
        expected = {
            "stub": {"STUB"},
            "real": {"SMOKE", "TRAINED"},
            "unavailable": {"UNAVAILABLE"},
        }
        if self.artifact_kind not in expected[self.model_mode]:
            raise ValueError("Inconsistent report provenance")
        return self
