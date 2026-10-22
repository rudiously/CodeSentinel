# Conventions

Python target is 3.11; use explicit types, small functions and Pydantic boundaries. Run ruff, black and strict mypy. Dynamic ML/library interfaces have explicit typed wrappers; only named third-party libraries without stubs use import overrides. No global relaxation of checks on project modules. pytest uses importlib collection to avoid duplicate test-module names.

TypeScript is strict with unused-code checks; ESLint and Prettier are configured. Frontend formatting/build/lint/tests are not yet verified because npm installation is blocked. `make setup/test/lint` includes frontend by default. `PYTHON_ONLY=1` explicitly skips frontend checks and must never be called a full-project pass. `VENV=/opt/anaconda3/bin` is the installed offline Python 3.13 fallback, not the pinned 3.11 environment.

Use snake_case Python functions/files, PascalCase React components, typed shared schemas in shared/. Backend owns orchestration, model_service owns HTTP inference, ml owns offline model lifecycle, action owns runner integration, deploy owns container/monitoring definitions, fixtures owns shared SYNTHETIC contract examples. Scanned source is data: never execute, import, compile or shell-interpolate it. User-supplied paths are validated relative paths, not local filesystem locations.

Application configuration uses pydantic-settings/environment variables with .env.example documenting each option. ML experiment configs are versioned YAML selected explicitly by CLI. Build-time frontend settings use VITE_ variables. No credentials or mutable production values in source/images. Hide settings inputs in validation errors. Use source-free structured JSON logging; disable uvicorn access logging on OAuth callback services so query codes/state do not enter logs. Error responses use shared error.code/message/request_id; ERROR scan reports are the explicitly documented Contract B exception to the common error body.

Pin direct Python requirements per service and ML; pin frontend package versions and base-image tags. The npm transitive lockfile and vulnerability remediation are pending network access; do not fabricate a lockfile or clean audit. CI runs pip-audit/npm audit and fails on audit errors. Prefer CPU Torch wheels on Linux for serving. Weights, datasets, mlruns/, databases, .env, virtualenvs and node_modules remain ignored.

Git policy: main must run; use feat/<task-id> and small conventional commits after verified tasks. PM bootstrapped the project-local repository on feat/p0-01-foundations at aea8746. Agent staging remains denied (.git/index.lock); never stage secrets, weights or unrelated files. No agent commit is claimed.

Any contract change updates Contracts.md, Architecture.md Decision Log, schemas, consumers, mocks and tests together. Every completed task needs observed verification recorded in Tasks.md/Progress.md. Keep unfinished or externally unverified gates BLOCKED; STUB, SMOKE and SYNTHETIC labels are mandatory wherever applicable.

Canonical remote: https://github.com/rudiously/CodeSentinel. Source push by PM is verified; GitHub connector reads work but writes still return 403. Normal-terminal Git is required until agent write access is available.
