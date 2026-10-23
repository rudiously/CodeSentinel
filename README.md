# CodeSentinel

Canonical GitHub repository: [rudiously/CodeSentinel](https://github.com/rudiously/CodeSentinel). Source is published on `feat/p0-01-foundations` at `aea8746`. Four CI image builds passed; Python typing and frontend formatting checks failed. Python fixes are verified locally and await publication; full CI is not green.

AI-assisted pull request security review: CodeBERT signal + static analysis + an explainable PASS/WARN/BLOCK policy. Dependency failures return **ERROR**, never silent PASS.

**Current state:** Python components and offline SMOKE integration are verified. Frontend source, Docker and CI definitions exist, but frontend installation, native analyzers, live containers, GitHub execution and full training remain unverified. Read [Progress.md](Progress.md) for observed commands and blockers. This is not a production-ready or validated vulnerability detector.

## Quickstart

Requires Python 3.11, Node 22+, Docker Desktop, internet access and repository write permission.

1. `cp .env.example .env`. Fill independent random JWT_SECRET, POSTGRES_PASSWORD and GRAFANA_ADMIN_PASSWORD (use URL-safe characters for the database password). For a local demonstration set ENVIRONMENT=development and DEV_LOGIN_ENABLED=true. Production forbids dev login and disabled authentication.
2. `make setup`. This installs pinned Python and frontend dependencies. Generate/review the npm lockfile, run `npm --prefix frontend run format`, then `make lint test` and `npm --prefix frontend run build`. The supplied frontend source has not yet passed these npm checks; see HumanActions H7.
3. **One-command stack startup:** `make up`. Migrations run before the backend serves. Then `bash scripts/wait_for_services.sh` and `PYTHON_BIN=.venv/bin/python bash scripts/e2e_demo.sh`.
4. Open [dashboard](http://localhost:3002), [API docs](http://localhost:8000/docs), [model health](http://localhost:8001/health), [Prometheus](http://localhost:9090), [Grafana](http://localhost:3001), [MLflow](http://localhost:5001). Grafana uses admin and your configured password.

`make down` stops services without deleting the database volume. No stack startup is claimed in this environment: Docker socket access and loopback binding are denied.

## Verified offline path on this workstation

```bash
make VENV=/opt/anaconda3/bin PYTHON_ONLY=1 lint test
CODESENTINEL_OFFLINE=1 PYTHON_BIN=/opt/anaconda3/bin/python bash scripts/smoke_test.sh
make VENV=/opt/anaconda3/bin train-smoke
```

This uses existing Python 3.13 tools, not the pinned Python 3.11 environment. PYTHON_ONLY explicitly skips frontend checks; it is not a full-project gate pass. The HTTP smoke is in-process (both service APIs), using real Python AST parsing, a limited built-in rule set and the deterministic STUB predictor. It demonstrates clean PASS and vulnerable BLOCK, not trained-model accuracy or Docker/TCP readiness. Defaults require tree-sitter and Bandit/cppcheck; opt-in alternatives are labelled in reports.

## Architecture

GitHub Action or signed webhook → backend extraction/static/model orchestration → pure risk engine → report and source-free database → PR comment/check and React dashboard. `model_service/` serves a versioned artifact independently of `backend/`. `ml/` owns data, training, validation-only calibration, export, integrity, attribution and evaluation. [Architecture.md](Architecture.md), [Contracts.md](Contracts.md), [Security.md](Security.md) describe exact boundaries.

Default risk: `.5*p_model + .5*max_static + .1 agreement bonus`, clamped to one. Static High=1, Medium=.6, Low=.3. Bonus applies when p>=.5 and s>=.6. PASS <.35, WARN <.65, otherwise BLOCK; High forces at least WARN. These are configurable initial policy values, not validated optimal thresholds.

## ML training and evaluation

`make train-smoke` creates a small CPU **SMOKE** artifact, tests PyTorch/TorchScript parity and records MLflow runs plus separate SMOKE registry versions. It uses tiny randomly initialized RoBERTa and synthetic snippets—not pretrained CodeBERT. The console prints the artifact version; verify with `python -m scripts.verify_smoke_artifact --artifact models/codesentinel-codebert/<version>`.

For full training follow [HumanActions.md](HumanActions.md) H8 and [Colab notebook](ml/notebooks/colab_train.ipynb). The verified dataset identity/license source is [ml/data/README.md](ml/data/README.md). Downloaded counts are pending. Trained artifact layout: `models/codesentinel-codebert/v1/{model.pt,tokenizer/,metadata.json,evaluation.json}`. TorchScript is the selected export format; no ONNX claim. Set MODEL_ARTIFACT_DIR directly, or MODEL_VERSION for Compose. Integrity mismatch fails closed. MODEL_ARTIFACT_DIR absent → explicit STUB.

```bash
python -m ml.data.download
python -m ml.data.split
python -m ml.train --config ml/configs/train_codebert.yaml
python -m ml.evaluation_run --artifact models/codesentinel-codebert/v1 --test ml/data/processed/test.jsonl --validation ml/data/processed/validation.jsonl --output docs/evaluation/trained-results.json
```

**PENDING: requires trained model artifact**. Earlier accuracy 64.09%, precision 60.40%, recall 63.34%, F1 61.83% are **earlier run, not reproduced**. No superiority claim is made. SMOKE evaluation outputs are explicitly labelled and cannot establish O7.

## GitHub integration

The primary composite Action uses GitHub-provided OIDC for `/scan` and GITHUB_TOKEN for comments; no manually stored CodeSentinel session is required. Enable GITHUB_OIDC_ENABLED, configure GITHUB_ALLOWED_REPOSITORIES and a reachable API URL, and grant the workflow `id-token: write`, `contents: read`, `pull-requests: write`. An optional API session token supports manual use. Workload identity is accepted only on `/scan`, for allowlisted repositories and pull_request subjects, with audience `codesentinel` and verified GitHub signature/issuer/expiry. Set repository variable CODESENTINEL_API_URL. See action/action.yml and .github/workflows/codesentinel-gate.yml. Other code languages fail closed rather than being called safe. GitHub enterprise/custom OIDC subjects are not supported by this initial implementation.

The App path verifies raw-body HMAC before parsing, obtains an installation token, collects complete post-change blobs, checks stable PR head, scans, comments and posts a check. Configure credentials per HumanActions H6. Delivery deduplication is in-memory, not durable. Fake HTTP and CLI tests passed; live GitHub actions were not performed.

## Dashboard and source handling

Pages: Login, Repositories, Scan History, Scan Detail, Analytics, Model Info. `VITE_USE_MOCKS=true` shows **SYNTHETIC** shared Contract B fixtures, with scanning disabled. Live STUB and SMOKE modes have explicit banners. New reports can highlight source/attribution lines; history intentionally retains no code or token text, so historical source views explain that limitation. Authentication is required by default.

## Limitations and references

Function-level C training does not validate Python/C++ performance; 512-token truncation loses context; sample splits do not establish held-out-repository generalization; exact deduplication misses clones. Moderate accuracy, false positives/negatives and distribution shifts require human review. SHA256 integrity assumes trusted metadata. Rate limiting and delivery deduplication are single-process. Dependency audits and native/container/browser verification are pending. Do not expose this unfinished demo publicly.

Existing research: [Devign](https://papers.nips.cc/paper/9209-devign-effective-vulnerability-identification-by-learning-comprehensive-program-semantics-via-graph-neural-networks), [CodeBERT](https://arxiv.org/abs/2002.08155), [GraphCodeBERT](https://arxiv.org/abs/2009.08366). Our contribution is integration and decision framework. See docs/demo-script.md, docs/viva-notes.md, docs/model-card.md and docs/report/.
