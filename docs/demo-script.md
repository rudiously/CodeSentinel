# Demonstration script

## Verified offline path
1. From the repository: `make VENV=/opt/anaconda3/bin PYTHON_ONLY=1 lint test` (uses installed fallback tools, not the pinned Python 3.11 environment).
2. Run `CODESENTINEL_OFFLINE=1 PYTHON_BIN=/opt/anaconda3/bin/python bash scripts/smoke_test.sh`.
3. Show clean PASS and vulnerable BLOCK with STUB labels. Explain Python AST and limited builtin rules are opt-in offline alternatives, not Bandit/tree-sitter.
4. Show risk-boundary, model-down, webhook signature and Action CLI tests in backend/tests and action/tests. BLOCK exits 1; ERROR exits 2.
5. Run `make VENV=/opt/anaconda3/bin train-smoke` to produce a new explicitly SMOKE artifact and registry version. The console prints model_version; use that directory in `python -m scripts.verify_smoke_artifact --artifact models/codesentinel-codebert/<printed-version>`.
6. Explain the zero parity difference measured on tested inputs, hash rejection and attribution line mapping; do not cite synthetic metrics as research performance.

## Full-stack path (NOT verified here)
1. Complete HumanActions.md dependencies, secrets and Docker access. `cp .env.example .env`; fill independent random secrets; for a local demo only set DEV_LOGIN_ENABLED=true and ENVIRONMENT=development.
2. Run `make setup && make lint test`, then `make up` and `bash scripts/wait_for_services.sh`.
3. Open http://localhost:3002, use DEV-ONLY login or configured OAuth, submit clean then vulnerable source. Show explicit model provenance and history. Historical source is deliberately not retained.
4. Run `PYTHON_BIN=.venv/bin/python bash scripts/e2e_demo.sh` (live TCP and service targets; requires credentials or dev login).
5. Open Grafana at http://localhost:3001 (admin and configured password), Prometheus at http://localhost:9090, MLflow at http://localhost:5001.
6. Open a test PR only after GitHub credentials/reachable API are configured. Show a real comment/check only if observed. Fake-GitHub tests are separate local evidence.

No screenshots or video have been fabricated. Full training and live demonstration remain pending.
