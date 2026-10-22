# Test plan and observed evidence

## Current local test command

`make VENV=/opt/anaconda3/bin PYTHON_ONLY=1 lint test`

Observed Python suite: **86 passed**, strict mypy succeeds on **82 source files**, ruff and black checks pass. Python 3.13 installed fallback; pinned Python 3.11 setup remains unverified. Notebook Python cells are separately syntax-checked after excluding Colab magics; Black skips notebooks because optional Jupyter formatting dependencies are absent. Frontend is explicitly skipped, not passing.

## Coverage

| Level | Tests / checks | Observed scope |
|---|---|---|
| Contracts | Shared fixtures, invalid probabilities, provenance and ERROR invariants | Passed |
| Risk unit | PASS/WARN/BLOCK boundaries, agreement bonus, max severity, High floor, ablations, unavailable model, invalid policy/probability | Passed |
| Parsing | Python decorators/async/Unicode ranges, invalid code, strict diff counts, deleted files, unsafe paths | Python AST fallback passed; native tree-sitter unavailable |
| Static tools | Builtin Python AST rules, no-execution marker, Bandit normalization/fixed argv, subprocess timeout/missing tool | Passed local/mock checks; real Bandit/cppcheck blocked |
| API | Validation, size limit, rate limit, model proxy, invalid/upstream failure, metrics | Passed in-process |
| Persistence | Actual SQLite Alembic upgrade/downgrade, normalized rows, history and source/token stripping, SYNTHETIC seed | Passed; PostgreSQL runtime blocked |
| Webhooks | HMAC before parsing, invalid/valid, unsupported replay, duplicate/retry | Passed |
| GitHub/Auth | Fake HTTP file blobs/comment/check, actual RSA App token exchange with fake HTTP, fake OAuth exchange/state, JWT expiry and production switches, RSA OIDC repo/audience scope | Passed locally; no live GitHub claim |
| Action | Actual CLI subprocess dry runs PASS=0/WARN=0/BLOCK=1/ERROR=2 | Passed |
| ML unit | Dedup/conflicts/disjoint seeded splits, validation-only calibration guard, measured metric functions, IG completeness/line mapping, hash/path rejection | Passed |
| Training/export | `make VENV=/opt/anaconda3/bin train-smoke` | Passed on synthetic tiny random RoBERTa, CPU; actual artifact/MLflow registry generated |
| Artifact runtime | `python -m scripts.verify_smoke_artifact --artifact models/codesentinel-codebert/smoke-v1-20261022170747528610` | Passed on latest artifact: batch/API/provenance/line mapping/hash rejection, with trained-performance field suppressed |
| Offline HTTP smoke | `CODESENTINEL_OFFLINE=1 PYTHON_BIN=/opt/anaconda3/bin/python bash scripts/smoke_test.sh` | Passed clean PASS/vulnerable BLOCK, STUB, both ASGI APIs in-process |
| Evaluation harness | `python -m ml.evaluation_run ... --analyzer-mode builtin-python` | Passed on explicitly SMOKE/synthetic examples; real trained evaluation pending |
| Deployment static | Docker Compose config --quiet with validation-only placeholders, YAML parse, Grafana JSON panels | Passed; not runtime evidence |
| Frontend | npm install, format/lint/test/build, mocks/live browser states | BLOCKED: ENOTCACHED/ENOTFOUND, no lockfile |
| Audits | pip-audit, npm audit | BLOCKED: module missing / ENOLOCK; no vulnerability-count claim |
| Frontend attempted commands | npm run build / lint / test | Each exit 127: tsc / eslint / vitest missing after failed installation |
| Live E2E | `make up`; `PYTHON_BIN=.venv/bin/python bash scripts/e2e_demo.sh` | BLOCKED: Docker socket and loopback binding denied |

## Gates

M0 skeleton passed in the offline environment before frontend implementation; the current full default Make gate has NOT passed. M1 has a passing offline Python/AST candidate, but full native/static acceptance remains blocked. M2 dashboard gate is blocked. M3 CPU smoke candidate is locally verified; it does not advance unresolved upstream milestones or replace full training. M4 live stack and M5 full definition of done remain blocked. No CI run or published image is claimed.

## Regression commands after dependencies return

1. `make setup && make test && make lint` (full Python 3.11 + frontend).
2. `PYTHON_BIN=.venv/bin/python bash scripts/smoke_test.sh` (default tree-sitter/Bandit).
3. `make train-smoke` and `python -m scripts.verify_smoke_artifact --artifact <printed-artifact-directory>`.
4. `make up`, wait for health, then `PYTHON_BIN=.venv/bin/python bash scripts/e2e_demo.sh`; inspect Grafana/Prometheus targets.
5. `npm --prefix frontend run dev` with VITE_USE_MOCKS=true and false; exercise all pages and source/attribution highlights.
6. Run `python -m ml.evaluation_run --artifact models/codesentinel-codebert/v1 --test ml/data/processed/test.jsonl --validation ml/data/processed/validation.jsonl --output docs/evaluation/trained-results.json` only after full training.

All trained-model evaluation documents retain **PENDING: requires trained model artifact**. No test or benchmark result is inferred from code presence.

## 2026-10-22 continuation
`make VENV=/opt/anaconda3/bin PYTHON_ONLY=1 lint test`: 86 passed in 4.74s; ruff/black and strict mypy (82 files) passed. New tests cover scan-wide signal fusion across functions, module-level finding weights, actual-decision metrics under High safety floors, non-finite score rejection, synthetic input provenance and pre-inference leakage guard. Offline STUB HTTP smoke again passed. GitHub remote read verified; initial write failed 403, not a successful publish.

## GitHub CI evidence (2026-10-22)
Run https://github.com/rudiously/CodeSentinel/actions/runs/39824257480 at aea8746: all four Docker builds passed, including frontend TypeScript/Vite production build. Python setup succeeded on 3.11; Ruff/Black passed, mypy failed at ml/train.py:94 and ml/predictor.py:77; tests therefore did not run in CI. Both calls are now fixed locally; local Python-only checks passed 86 tests in 4.84s. Frontend ESLint passed, Prettier failed 17 files, subsequent test/build/audit steps were skipped. npm installation reported 18 vulnerabilities (3 moderate, 13 high, 2 critical); detailed advisories not yet retrieved. No clean audit claim.
