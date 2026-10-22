# Human Actions
## H1 — Publish follow-up commits
PM completed initialization and initial push: feat/p0-01-foundations at aea8746, correct origin. Agent `git add` still fails creating .git/index.lock (Operation not permitted).
1. From a normal terminal, review git diff and stage only reviewed source/docs, including models/README.md; never weights, .env or databases.
2. Commit the verified Python typing fix and memory changes with a conventional message, then push the existing feature branch.
3. Current commit uses placeholder identity Your Name <your.email@example.com>; configure your preferred Git identity for future commits if desired. Do not rewrite published history automatically.
Unblocks: follow-up CI verification and per-task commits.
## H2 — Full training
Colab pipeline is now implemented; follow H8 for exact steps. Do not report earlier metrics as reproduced.
Unblocks: trained-model evaluation, O1/O7 evidence.

## H3 — Restore pinned dependency access
1. Run `make setup` on a machine with working PyPI DNS/network.
2. Run `make lint test` using the installed Python 3.11 virtual environment.
Observed installation failed resolving the package index; installed Anaconda tools permit preliminary checks only.
Unblocks: pinned Python 3.11 reproducibility verification; offline M0 already passed with the explicitly recorded VENV override.

## H4 — Verify native extraction and static analyzers
1. Restore package access, then install backend/requirements.txt (tree-sitter grammars and Bandit are pinned there once added).
2. Use the backend container with Debian cppcheck 2.10-2, or install a compatible local cppcheck and record its actual version.
3. Run `PYTHON_BIN=.venv/bin/python bash scripts/smoke_test.sh` without CODESENTINEL_OFFLINE.
4. Run C/C++ extraction and static regression tests on examples; these are not verified in the offline environment.
Offline command verified: `CODESENTINEL_OFFLINE=1 PYTHON_BIN=/opt/anaconda3/bin/python bash scripts/smoke_test.sh`. It uses actual Python AST rules and two service APIs in-process, not Bandit/tree-sitter/Docker or TCP transport.
Unblocks: full P1-03/P1-05/M1 acceptance.
## H5 — Docker daemon access
Observed `docker info --format '{{.ServerVersion}}'` denied access to Docker socket by host policy.
1. Start Docker Desktop and allow this workspace Docker access if your client supports it.
2. Once deploy files exist, run `make up` and `bash scripts/e2e_demo.sh`.
Unblocks: image builds and live full-stack M4 gate. No live Docker results claimed.

## H6 — Configure GitHub OAuth, App and PR gate
1. Create a GitHub OAuth App, callback `http://localhost:8000/auth/github/callback` (use the deployed HTTPS URL later). Set GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET in .env. Set GITHUB_ALLOWED_USER_IDS to a JSON array of allowed numeric GitHub user IDs as strings.
2. Generate JWT_SECRET with `python3.11 -c 'import secrets; print(secrets.token_urlsafe(48))'` and put the result in .env; never commit it. Development demo: ENVIRONMENT=development and DEV_LOGIN_ENABLED=true. Production: ENVIRONMENT=production, DEV_LOGIN_ENABLED=false, AUTH_REQUIRED=true.
3. Create a GitHub App with repository Contents read, Pull requests write, Checks write; subscribe to pull_request. Configure reachable `/webhook/github`, generate a random GITHUB_WEBHOOK_SECRET and set the same secret in the App.
4. Install the App on a test repo. Set GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, GITHUB_APP_PRIVATE_KEY (PEM, literal newlines or escaped `\n`) in environment. GITHUB_TOKEN can alternatively be a manually supplied installation token; manual tokens expire and are not refreshed.
5. Primary Action path needs no App or stored API session: set repository variable CODESENTINEL_API_URL to a reachable API. Set GITHUB_OIDC_ENABLED=true and GITHUB_ALLOWED_REPOSITORIES=["owner/repo"] on the backend. Keep audience codesentinel or configure matching audience in the Action. Workflow permissions must include id-token:write, contents:read and pull-requests:write. GitHub supplies OIDC identity and GITHUB_TOKEN. CODESENTINEL_API_TOKEN is optional for manual session use, not required for CI.
6. Open a deliberately vulnerable PR in the test repo. Confirm a comment and failed gate; configure branch protection to require `CodeSentinel gate / gate`. Fork PRs without secrets fail closed; do not use pull_request_target to expose secrets.
Unblocks: live OAuth/App/PR demonstration; P2-03/P2-04 real-service verification. Local fake GitHub tests passed; no live remote write performed.

## H7 — Install and verify the dashboard
Observed offline npm ENOTCACHED and online npm ENOTFOUND registry.npmjs.org. Local installation remains blocked. Remote installation and frontend Docker production build passed; ESLint passed but Prettier failed 17 files; tests/browser remain unverified. npm reported 18 vulnerabilities (3 moderate, 13 high, 2 critical).
1. Restore npm registry/DNS access. From frontend/: `npm install --ignore-scripts`.
2. Run `npm run format` to format the authored source, then `npm run lint && npm test && npm run build`. Fix any newly revealed TypeScript/ESLint issues. No clean frontend claim is made until this succeeds.
3. Commit the generated package-lock.json after review. Replace npm install with npm ci in frontend/Dockerfile and CI to lock transitive dependencies.
4. Run `npm audit --audit-level=high`; review and fix reported issues, update exact pins and lockfile together. Python audit requires `pip-audit --progress-spinner off` after make setup. Neither audit is available/verified here.
5. Test VITE_USE_MOCKS=true and false. Check all six pages, filters, live scan/code highlights, OAuth/dev login, mobile width, error/loading/empty states and provenance labels. No browser screenshots are supplied as evidence yet.
Unblocks: P2-05/P2-06/M2, frontend CI/build, dependency audit portions of P5-04.

## H8 — Dataset download and full training
1. Publish the reviewed source to rudiously/CodeSentinel after H1/H11 so Colab can clone it. Open ml/notebooks/colab_train.ipynb in Colab, enable a GPU if available, mount Drive and verify the prefilled REPO_URL and select the actual reviewed REPO_REF. Pin a reviewed immutable commit where possible.
2. Execute cells in order. Review ml/data/README.md licenses and the downloaded provenance.json. Do not assume proposed split counts; use the generated processed/report.json.
3. The notebook sets output to Drive/MyDrive/CodeSentinel/models/codesentinel-codebert/v1 and MLflow sqlite storage on Drive. Best checkpoints are persisted under the sibling checkpoints directory. If interrupted, best weights survive; automatic optimizer/RNG resume is not implemented. Restart with a fresh version/output; do not overwrite a completed artifact.
4. Confirm metadata.json artifact_kind=TRAINED, validation calibration, actual test evaluation and export_parity. Copy the ENTIRE v1 folder locally under models/codesentinel-codebert/v1/. Never commit weights/data.
5. Set MODEL_ARTIFACT_DIR locally (or MODEL_VERSION=codesentinel-codebert/v1 for Compose), restart model_service and confirm /health says real/TRAINED. Run the trained evaluation command in docs/evaluation/model-metrics.md.
6. Review ablation and error analysis honestly. O7 is not satisfied unless measurements support a comparative benefit; report a negative result if observed.
Unblocks: P3-01 real data verification, O1/O7, all real-model evaluation evidence. Earlier metrics remain “earlier run, not reproduced”.

## H9 — Run deployment and CI gates
1. Complete H1/H3/H4/H5/H6/H7; fill POSTGRES_PASSWORD, GRAFANA_ADMIN_PASSWORD and JWT_SECRET in .env using independent URL-safe random values. Do not commit .env. Local demo may enable DEV_LOGIN_ENABLED=true; production forbids it.
2. Run `make setup && make test && make lint`. Run `make up`; wait for healthchecks using scripts/wait_for_services.sh. Run `PYTHON_BIN=.venv/bin/python bash scripts/e2e_demo.sh` and inspect Prometheus active targets plus Grafana panels.
3. Verify non-root image execution and volume permissions (Postgres uid 70, model/backend/MLflow uid 10001, frontend uid 101, Grafana uid 472). Dockerfiles/Compose have only passed static configuration checks here; image availability, apt package pin, health commands and startup are unverified.
4. Run CI on GitHub. Required permissions: contents:read for CI; pull-requests:write for gate; packages:write for tag releases. Audit failures are not waived. After reviewed successful checks, tag a version to publish images to GHCR; no image push or deployment was performed by this agent.
Unblocks: P4-01/P4-02/P4-03/M4/M5 and live observability evidence. Kubernetes remains STRETCH and is intentionally not implemented before CORE completion.

## H10 — Permit live local network services
A direct loopback bind to 127.0.0.1 with an ephemeral port failed: PermissionError [Errno 1] Operation not permitted.
1. Use a normal local terminal or enable loopback listening for this workspace.
2. After dependencies/migrations, run backend/model uvicorn with --no-access-log to avoid logging OAuth callback queries.
3. Run the LIVE e2e script after the full stack starts. In-process ASGI checks are not TCP or browser evidence.
Unblocks: direct local service/browser verification in addition to Docker access.

## H11 — GitHub source publication status
The PM initialized and pushed `feat/p0-01-foundations` at `aea8746dfad4593f9f34b809b413fdc464cfa511`. GitHub CI run 39824257480 completed: all four Docker image builds passed; Python failed on two third-party untyped calls, frontend failed Prettier checks in 17 files. Local fixes for both Python calls pass 86 tests, Ruff, Black and strict mypy (82 files). These fixes have not been pushed. Git staging still fails creating .git/index.lock; connector writes remain HTTP 403. Local npm/PyPI and Docker access remain blocked.

Initial publication is complete. For further agent publication, enable project Git writes if supported, or commit/push from a normal terminal (H1). Do not recreate the repository or force-push. Keep the feature branch until CI and required gates pass; main does not exist yet. Colab must select the actual reviewed branch/immutable commit instead of assuming main.
Unblocks: publishing current corrections and remote verification.
