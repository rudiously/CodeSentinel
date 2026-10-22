# Contracts
Version 1.0 — 2026-10-22. All examples are SYNTHETIC; predictions are STUB.
## A: Python model interface
```python
def predict(code: str, language: str = "c") -> Prediction: ...
def predict_batch(codes: list[str], language: str = "c") -> list[Prediction]: ...
```
Prediction is the JSON shape below. Probability is finite in [0,1]; label uses artifact validation threshold (stub: .5). token_importance entries: {"token": str, "line": int, "importance": float}; lines are one-based. Empty attribution means unavailable, never fabricated. Supported language identifiers: c, cpp, python. Real model non-C performance is unvalidated. Max 100000 characters/input, 32 batch items. CodeBERT uses 512 tokens, truncation by default. model_mode is stub or real; artifact_kind is STUB, SMOKE, TRAINED. SMOKE is never trained evaluation evidence.
```json
{
  "probability": 0.1,
  "label": "SAFE",
  "token_importance": [],
  "model_version": "stub-v1",
  "model_mode": "stub",
  "artifact_kind": "STUB"
}
```
## B: Scan report
Request POST /scan: {"repository":"demo/example","files":[{"path":"clean.py","language":"python","code":"def add(a,b):\n return a+b"}],"mode":"combined"}. Optional diff string filters full source to changed functions; complete post-change files remain REQUIRED. Diff-only scanning is rejected because hunks are not complete source. Maximum 50 files / 200 functions / 1000000 total request bytes. Modes: combined, model_only, static_only.
Decision values PASS, WARN, BLOCK, ERROR. Failed analysis never produces PASS. ERROR has null risk_score; failed function probability may be null. Severity uses High, Medium, Low. Findings: {"file":str,"rule":str,"severity":str,"line":int,"message":str}. Every function includes code for transient display; persistence must exclude source by default. Attribution lines in reports are absolute file lines. Synthetic fixture:
```json
{
  "scan_id": "00000000-0000-4000-8000-000000000001",
  "repository": "demo/example",
  "decision": "PASS",
  "risk_score": 0.05,
  "functions": [
    {
      "name": "add",
      "file": "clean.py",
      "start_line": 1,
      "end_line": 2,
      "probability": 0.1,
      "risk_score": 0.05,
      "decision": "PASS",
      "code": "def add(a, b):\n    return a + b",
      "token_importance": []
    }
  ],
  "findings": [],
  "reasons": [
    "STUB: no static findings; add model probability 0.10."
  ],
  "model_version": "stub-v1",
  "model_mode": "stub",
  "artifact_kind": "STUB",
  "synthetic": true,
  "timestamp": "2026-10-22T12:00:00Z",
  "errors": [],
  "analysis": {
    "static_analyzer_mode": "builtin-python",
    "extractor_modes": [
      "python-ast"
    ],
    "ablation_mode": "combined"
  }
}
```
## C: Model-service HTTP (port 8001)
- POST /predict request {"code":"int add(int a,int b){return a+b;}","language":"c"}; response Contract A.
- POST /predict_batch request {"codes":["int f(){return 1;}"],"language":"c"}; response {"predictions":[Contract A]} preserving order.
- GET /health response {"status":"ok","model_mode":"stub","artifact_kind":"STUB","model_version":"stub-v1"}.
- GET /model/info: health fields plus metrics (null if unavailable), thresholds {"classification":0.5}, limitations array.
- GET /metrics: Prometheus text.
Validation 422, size 413, dependency unavailable 503; errors follow {"error":{"code":"MODEL_UNAVAILABLE","message":"Model service unavailable","request_id":"uuid"}}. Clients use 10s timeout, at most one retry for connection failures, never silently substitute stub for failed real inference. No source in logs.
## Webhooks
Verify raw bytes against X-Hub-Signature-256 using HMAC-SHA256 and compare_digest BEFORE JSON parsing. Supported event pull_request, actions opened/synchronize/reopened. Unsupported events return {"status":"ignored"}; invalid signature 401. Deduplicate X-GitHub-Delivery before posting duplicate checks. Only api.github.com URLs built from validated owner/repo identifiers may be fetched; reject arbitrary payload URLs.
## DB summary
users(id, github_id unique, login); repos(id, owner, name, user_id); scans(id, repo_id, timestamp, decision, risk_score nullable, model_version, model_mode, artifact_kind, synthetic, reasons JSON); scan_functions(id, scan_id, name, file, start_line, end_line, probability nullable, risk_score nullable, decision); findings(id, scan_id, function_id nullable, rule, severity, line, file, message). Foreign keys required; source not stored by default.
## Change log
2026-10-22: Initial v1.0; extends Work.md illustrative contracts with explicit ERROR, provenance and mode labels, batch and model-info endpoints per PM instructions. All consumers must use these exact names.

## v1.1 validation clarifications (2026-10-22)
Executable schemas in shared/schemas.py are reused by API, fixtures and consumers. ERROR reports use null risk. If model metadata is unavailable, model_mode="unavailable", artifact_kind="UNAVAILABLE" and model_version="unavailable"; these labels cannot appear on a successful prediction. Analysis errors always produce ERROR. No existing prediction shape changes. All probabilities and scores must be finite and within [0,1].

## v1.2 analysis provenance (2026-10-22)
Reports include required analysis={"static_analyzer_mode":"external"|"builtin-python", "extractor_modes":["tree-sitter"|"python-ast"|"whole-file"], "ablation_mode":"combined"|"model_only"|"static_only"}. Python AST extraction and limited built-in rules are opt-in offline alternatives; never represented as tree-sitter or Bandit. Default missing analyzers fail with ERROR. /scan ERROR returns HTTP 503 with the full Contract B report, not a PASS or transport error schema; pre-scan request failures use the common error schema. static_only performs no model inference and reports unavailable model provenance.

## v1.3 artifact and authentication semantics (2026-10-22)
- TorchScript artifact: model.pt, tokenizer/, evaluation.json, metadata.json. Metadata covers all non-metadata files with SHA256, weight hash, dataset hash, config provenance, thresholds/temperature, artifact_kind, git commit, MLflow identity and export parity. No ONNX format is claimed. `model_mode=real` can pair with SMOKE or TRAINED; SMOKE metrics are suppressed from the normal model-info performance field.
- New exported artifacts support signed integrated-gradients token importance. Offsets become one-based function lines and then absolute file lines in Contract B. Importance is normalized by absolute attribution mass, can be negative, and is not causal evidence. EXPLAIN_STEPS=0 disables; legacy artifacts return empty attribution.
- Backend aliases POST /analyze-pr and /score-file use the exact ScanRequest body as /scan. POST /analyze uses {code,language} and returns {findings,static_analyzer_mode}. GET /history returns a list of Contract B reports with code="" and token_importance=[]; limit<=200, offset>=0, optional repository and decision filters. GET /history/{scan_id} returns one report or common 404 error. GET /repos returns [{id,repository}]. All are protected by default.
- Auth: GET /auth/config returns dev_login_enabled,github_enabled,auth_required. POST /auth/dev returns {access_token,token_type:"bearer",dev_only:true,expires_in}; disabled by default and forbidden in production. GET /auth/github redirects with browser-bound state; callback returns a frontend fragment session, not a query token. Session JWT issuer codesentinel, audience codesentinel-api, exp/iat/sub/jti required.
- Primary Action authentication: optional API session, otherwise GitHub Actions OIDC (audience codesentinel by default), plus GITHUB_TOKEN only for GitHub comments. Backend verifies fixed GitHub issuer/JWKS, RS256, exp/iat/nbf/sub/repository/event_name, allowlisted repo and pull_request subject. Workload identity only authorizes POST /scan; body.repository must match the verified claim. No manually stored CodeSentinel token is required for CI. Live OIDC remains unverified. See GitHub primary reference: https://docs.github.com/en/actions/reference/security/oidc .
- Webhook delivery dedup is a bounded per-process TTL cache, not durable. App scans complete changed file blobs (whole-file scope), rejects unsupported file types, and checks stable PR head; it does not execute source. A webhook handler failure removes delivery ID to permit retry.
- Every contract update above is reflected in schemas, service, mocks and tests. Updated shared fixture is fixtures/scan_report.json and its frontend copy. Historical source is deliberately unavailable, not reconstructed.

## v1.4 repository summaries (2026-10-22)
GET /repos items include `latest_scan`: null or {"decision":"PASS","risk_score":0.05,"artifact_kind":"STUB","timestamp":"2026-10-22T12:00:00+00:00"}. This is metadata only. Backend query, frontend type/card, mock and persistence test updated together.

## v1.5 scan-level aggregation (2026-10-22)
Contract B decision/risk_score combines `max(function.probability)` with the maximum static severity across the scan, as Project.md Document 10 specifies. These signals may come from different functions/files. Per-function rows retain their own scores, so scan risk is not defined as the maximum row score. Reasons identify the strongest model function and finding locations. Out-of-function static findings use the requested ablation mode instead of silently switching to static_only. Transport/schema fields are unchanged; frontend label is SCAN RISK, and simple single-function fixtures remain valid unchanged. Regressions verify cross-function agreement and module-level weighted severity.

Evaluation JSON (not a new HTTP contract): confusion-matrix/accuracy/precision/recall/F1 fields use actual PASS/WARN/BLOCK decisions so High safety overrides are counted. `prediction_source="decisions"` and `threshold=null` distinguish policy decisions from raw-score threshold metrics. PR curves remain score-based and declare that basis. ERROR analyses are rejected rather than counted as binary predictions. Synthetic sample provenance also forces synthetic labelling even with a TRAINED artifact; validation/test overlap is rejected before model load/inference.
