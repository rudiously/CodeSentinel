"""Contract B orchestration: every failed dependency produces an ERROR report."""

from datetime import datetime, timezone
from uuid import uuid4
from time import perf_counter

from backend.app.schemas import ScanRequest
from backend.app.services.diff_parser import parse_diff, safe_path
from backend.app.services.function_extractor import Function, extract_functions
from backend.app.services.model_client import ModelClient
from backend.app.services.risk_engine import RiskConfig, score_risk
from backend.app.services.static_analysis.base import analyze
from backend.app.settings import Settings
from shared.http import ServiceError
from shared.schemas import Finding, FunctionReport, ScanReport


def build_report(
    body: ScanRequest, settings: Settings, model: ModelClient
) -> ScanReport:
    if len(body.files) > settings.max_files:
        raise ServiceError("TOO_MANY_FILES", "Scan exceeds configured file limit", 413)
    changed = (
        {f.path: f for f in parse_diff(body.diff, settings.max_files)}
        if body.diff
        else None
    )
    if changed and any(
        not f.deleted and p not in {source.path for source in body.files}
        for p, f in changed.items()
    ):
        raise ServiceError(
            "MISSING_SOURCE",
            "Diff requires complete post-change source for every changed file",
            422,
        )
    functions: list[FunctionReport] = []
    all_findings: list[Finding] = []
    reasons: list[str] = []
    errors: list[str] = []
    predictions = []
    extractors: set[str] = set()
    config = RiskConfig(
        settings.risk_model_weight,
        settings.risk_static_weight,
        settings.risk_agreement_bonus,
        settings.risk_warn_threshold,
        settings.risk_block_threshold,
    )
    deadline = perf_counter() + settings.scan_timeout_seconds
    for source in body.files:
        safe_path(source.path)
        if len(source.code) > settings.max_code_chars:
            raise ServiceError(
                "CODE_TOO_LARGE", "Source exceeds configured character limit", 413
            )
        if changed is not None and (
            source.path not in changed or changed[source.path].deleted
        ):
            continue
        try:
            if perf_counter() > deadline:
                raise ServiceError(
                    "SCAN_TIMEOUT", "Scan exceeded its configured time budget"
                )
            extracted = extract_functions(
                source.code,
                source.language,
                source.path,
                allow_python_ast=settings.allow_python_ast,
            )
            # Static analysis includes module-level code and unsupported function constructs.
            findings = (
                analyze(
                    source.code,
                    source.language,
                    source.path,
                    settings.static_analysis_mode,
                )
                if body.mode != "model_only"
                else []
            )
            all_findings.extend(findings)
            if changed is not None:
                lines = changed[source.path].changed_lines
                extracted = [
                    f
                    for f in extracted
                    if any(f.start_line <= line <= f.end_line for line in lines)
                ]
            if not extracted:
                # Conservative whole-file fallback is explicit, not a guessed function.
                extracted = [
                    Function(
                        "<file>",
                        source.path,
                        1,
                        max(1, len(source.code.splitlines())),
                        source.code,
                        source.language,
                        "whole-file",
                    )
                ]
            if len(functions) + len(extracted) > settings.max_functions:
                raise ServiceError(
                    "TOO_MANY_FUNCTIONS", "Scan exceeds configured function limit", 413
                )
            for function in extracted:
                if perf_counter() > deadline:
                    raise ServiceError(
                        "SCAN_TIMEOUT", "Scan exceeded its configured time budget"
                    )
                extractors.add(function.extractor)
                relevant = [
                    f
                    for f in findings
                    if function.start_line <= f.line <= function.end_line
                ]
                prediction = (
                    model.predict(function.code, source.language)
                    if body.mode != "static_only"
                    else None
                )
                if perf_counter() > deadline:
                    raise ServiceError(
                        "SCAN_TIMEOUT", "Scan exceeded its configured time budget"
                    )
                if prediction:
                    predictions.append(prediction)
                result = score_risk(
                    prediction.probability if prediction else None,
                    relevant,
                    function.name,
                    body.mode,
                    config,
                )
                functions.append(
                    FunctionReport(
                        name=function.name,
                        file=function.file,
                        start_line=function.start_line,
                        end_line=function.end_line,
                        probability=prediction.probability if prediction else None,
                        risk_score=result.risk_score,
                        decision=result.decision,
                        code=function.code,
                        token_importance=(
                            [
                                token.model_copy(
                                    update={
                                        "line": token.line + function.start_line - 1
                                    }
                                )
                                for token in prediction.token_importance
                            ]
                            if prediction
                            else []
                        ),
                    )
                )
                reasons.extend(result.reasons)
            covered = {
                f.line
                for function in extracted
                for f in findings
                if function.start_line <= f.line <= function.end_line
            }
            # Findings outside changed functions still affect gate safety.
            outside = [f for f in findings if f.line not in covered]
            if outside:
                if len(functions) >= settings.max_functions:
                    raise ServiceError(
                        "TOO_MANY_FUNCTIONS",
                        "Scan exceeds configured function limit",
                        413,
                    )
                result = score_risk(
                    0.0, outside, "<file static findings>", body.mode, config
                )
                functions.append(
                    FunctionReport(
                        name="<file static findings>",
                        file=source.path,
                        start_line=1,
                        end_line=max(1, len(source.code.splitlines())),
                        probability=None,
                        risk_score=result.risk_score,
                        decision=result.decision,
                        code="",
                        token_importance=[],
                    )
                )
                reasons.extend(result.reasons)
        except ServiceError as exc:
            if exc.status == 413:
                raise
            errors.append(f"{source.path}: {exc.code}: {exc.message}")
    if not functions and not errors:
        errors.append("No supported source could be analyzed")
    if (
        predictions
        and len({(p.model_mode, p.artifact_kind, p.model_version) for p in predictions})
        != 1
    ):
        errors.append("Model changed during scan; retry with a stable artifact")
    first = predictions[0] if predictions else None
    strongest = max(
        (function for function in functions if function.probability is not None),
        key=lambda function: function.probability or 0.0,
        default=None,
    )
    # Document 10 combines the riskiest model function with the strongest finding
    # across the scan, even when these signals come from different functions/files.
    origin = f"{strongest.file}:{strongest.name}" if strongest else "no model signal"
    aggregate = score_risk(
        strongest.probability if strongest else None,
        all_findings,
        f"scan (highest model signal: {origin})",
        body.mode,
        config,
        analysis_error="; ".join(errors) if errors else None,
    )
    decision, risk = aggregate.decision, aggregate.risk_score
    reasons = aggregate.reasons + reasons
    return ScanReport.model_validate(
        {
            "scan_id": str(uuid4()),
            "repository": body.repository,
            "decision": decision,
            "risk_score": risk,
            "functions": [f.model_dump() for f in functions],
            "findings": [f.model_dump() for f in all_findings],
            "reasons": reasons + errors,
            "model_version": first.model_version if first else "unavailable",
            "model_mode": first.model_mode if first else "unavailable",
            "artifact_kind": first.artifact_kind if first else "UNAVAILABLE",
            "synthetic": False,
            "timestamp": datetime.now(timezone.utc),
            "errors": errors,
            "analysis": {
                "static_analyzer_mode": settings.static_analysis_mode,
                "extractor_modes": sorted(extractors),
                "ablation_mode": body.mode,
            },
        }
    )
