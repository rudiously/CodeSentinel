"""Pure deterministic risk policy. No network, state, side effects or trained claims."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from shared.schemas import Decision, Finding, Mode


@dataclass(frozen=True)
class RiskConfig:
    model_weight: float = 0.5
    static_weight: float = 0.5
    agreement_bonus: float = 0.1
    warn_threshold: float = 0.35
    block_threshold: float = 0.65

    def __post_init__(self) -> None:
        values = (
            self.model_weight,
            self.static_weight,
            self.agreement_bonus,
            self.warn_threshold,
            self.block_threshold,
        )
        if not all(isfinite(v) and 0 <= v <= 1 for v in values):
            raise ValueError("Risk configuration must be finite and within [0,1]")
        if abs(self.model_weight + self.static_weight - 1) > 1e-9:
            raise ValueError("Risk weights must sum to one")
        if not 0 < self.warn_threshold < self.block_threshold <= 1:
            raise ValueError("Invalid risk thresholds")


@dataclass(frozen=True)
class RiskResult:
    decision: Decision
    risk_score: float | None
    reasons: list[str]


def score_risk(
    probability: float | None,
    findings: list[Finding],
    function_name: str,
    mode: Mode = "combined",
    config: RiskConfig | None = None,
    *,
    analysis_error: str | None = None,
) -> RiskResult:
    policy = config or RiskConfig()
    if mode not in {"combined", "model_only", "static_only"}:
        raise ValueError("Unsupported ablation mode")
    if analysis_error or (mode != "static_only" and probability is None):
        return RiskResult(
            "ERROR",
            None,
            [f"{function_name}: analysis unavailable; gate must report an error."],
        )
    if probability is not None and (
        not isfinite(probability) or not 0 <= probability <= 1
    ):
        raise ValueError("Probability must be finite and within [0,1]")
    severity = {"High": 1.0, "Medium": 0.6, "Low": 0.3}
    static = max((severity[f.severity] for f in findings), default=0.0)
    p = probability if probability is not None else 0.0
    if mode == "model_only":
        risk = p
    elif mode == "static_only":
        risk = static
    else:
        risk = policy.model_weight * p + policy.static_weight * static
        if p >= 0.5 and static >= 0.6:
            risk += policy.agreement_bonus
    risk = min(1.0, risk)
    decision: Literal["PASS", "WARN", "BLOCK"] = (
        "PASS"
        if risk < policy.warn_threshold
        else "WARN" if risk < policy.block_threshold else "BLOCK"
    )
    reasons = [
        f"{function_name}: {mode} risk {risk:.3f}; model probability {p:.3f}, maximum static severity {static:.1f}."
    ]
    reasons.extend(
        f"{function_name}: {f.severity} {f.rule} at {f.file}:{f.line}: {f.message}"
        for f in findings
    )
    if static == 1.0 and decision == "PASS":
        decision = "WARN"
        reasons.append(f"{function_name}: High static finding forces at least WARN.")
    return RiskResult(decision, risk, reasons)
