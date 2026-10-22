# Tasks

DONE means the stated local implementation acceptance was verified, with limits explicit below. BLOCKED gates are not waived: downstream independent work follows the PM instruction to build around human blockers; it does not advance unresolved milestones. Source documents remain unchanged. No git commits were possible (H1).

| ID | Role | Acceptance criteria / observed limitation | Dependencies | Scope | Status |
|---|---|---|---|---|---|
| P0-01 | DEVOPS | Directories/config/memory exist; source documents untouched; foundation test passes. Git commits blocked H1. | none | CORE | DONE |
| P0-02 | DEVOPS | Conventions and typed toolchain checks pass offline. Exact pinned setup blocked H3; no 3.11 claim. | P0-01 | CORE | DONE |
| P0-03 | DOCS | A/B/C schemas, exact fixtures and error/provenance rejection tests pass; frontend fixture equals shared fixture. | P0-02 | CORE | DONE |
| M0 | DEVOPS | Historical empty-but-wired Python skeleton lint/test passed with VENV override. Current full default gate includes frontend and is blocked. | P0-03 | CORE | DONE |
| P1-01 | ML | Contract C STUB, env limits, uniform errors, metrics and non-root image definition; 12-test stage passed; image build pending H5. | M0 | CORE | DONE |
| P1-02 | BE | Settings, JSON metadata logs, health, validated timeout/retry model client, CORS and limiter; API error tests pass. | P1-01 | CORE | DONE |
| P1-03 | BE | Tree-sitter adapter and strict diff parser written; AST fallback/ranges/paths/diff tests pass. Native C/C++/Python grammar verification blocked H4. | P1-02 | CORE | BLOCKED |
| P1-04 | BE | Pure configured risk with thresholds, High floor, bonus, ablations, ERROR and invalid input unit tests passed. | P1-03 | CORE | DONE |
| P1-05 | BE | Bandit/cppcheck wrappers and normalization/timeout tests written; builtin Python rules tested without source execution. Native-tool regression blocked H4. | P1-04 | CORE | BLOCKED |
| P1-06 | BE | Complete blobs plus optional diff to Contract B; scan-wide max model + max static fusion, model-down, caps and module findings verified. Contract v1.5 regressions pass. | P1-05 | CORE | DONE |
| M1 | BE | Offline in-process two-service smoke clean PASS / vulnerable BLOCK passes, labelled STUB. Full native scanner gate blocked H4; no gate advancement claimed. | P1-06 | CORE | BLOCKED |
| P2-01 | BE | Five SQLAlchemy tables; SQLite Alembic upgrade/downgrade, persistence/redaction, history/repos/detail verified. Postgres runtime pending H5. | M1 | CORE | DONE |
| P2-02 | BE | HMAC before JSON, valid/invalid, unsupported replay, duplicate/retry tests pass; cache explicitly in-memory. | P2-01 | CORE | DONE |
| P2-03 | BE | Fixed-origin GitHub/App client and Action comment/check behavior verified with fake HTTP and RSA token exchange; CLI BLOCK=1/ERROR=2. Live GitHub H6 pending. | P2-02 | CORE | DONE |
| P2-04 | BE | JWT expiry/claims, prod-safe dev switch, browser-bound OAuth fake exchange tested; real OAuth H6 pending. OIDC workload identity tested locally. | P2-03 | CORE | DONE |
| P2-05 | FE | Six React pages on labelled shared mocks written. npm install/format/lint/test/build/browser verification blocked H7. | P2-04 | CORE | BLOCKED |
| P2-06 | FE | Typed live API client, auth and transient source display written. Real browser/API wiring blocked H7/H10. | P2-05 | CORE | BLOCKED |
| P2-07 | BE | Seed creates three explicitly SYNTHETIC/STUB records; actual SQLite persistence test passed. | P2-06 | CORE | DONE |
| M2 | FE | API-created persisted scans and fake GitHub/CLI gate pass locally; dashboard gate blocked H7. No milestone advancement. | P2-07 | CORE | BLOCKED |
| P3-01 | ML | Verified source ID/license references; download/clean/split code and synthetic leakage tests pass. Real download/counts blocked H8. | M2 | CORE | BLOCKED |
| P3-02 | ML | Seeded YAML training, class weights, batched validation, early stopping, durable best checkpoints and MLflow; actual CPU SMOKE train passed. | P3-01 | CORE | DONE |
| P3-03 | ML | Evaluation and validation-only temperature/recall threshold functions tested and executed in SMOKE; full metrics pending H8. | P3-02 | CORE | DONE |
| P3-04 | ML | IG completeness/offset unit tests plus actual exported SMOKE token/line attribution check passed; limitations documented. | P3-03 | CORE | DONE |
| P3-05 | ML | TorchScript/PyTorch parity measured 0.0 maximum difference on tested SMOKE inputs; versioned MLflow registry and complete manifest; tampering rejected. | P3-04 | CORE | DONE |
| P3-06 | ML | Verified artifact loads real/SMOKE in Contract C, batch/API checks pass; invalid artifact fails closed; smoke performance hidden from trained metrics. | P3-05 | CORE | DONE |
| P3-07 | ML | Colab notebook/Drive instructions written and Python cells syntax-checked; live Colab/full training explicitly H8. | P3-06 | CORE | DONE |
| M3 | ML | Local CPU SMOKE train/export/registry/load/HTTP/integrity candidate passed. Milestone advancement remains blocked by unresolved M1/M2 gates. | P3-07 | CORE | BLOCKED |
| P4-01 | DEVOPS | Seven-service Compose, dev overrides, healthchecks and automatic migrations defined; Compose config passes. Live make up blocked H5/H10. | M3 | CORE | BLOCKED |
| P4-02 | DEVOPS | CI includes lint/types/tests/smoke/frontend/images/audits and cache. Python local checks pass; frontend/audits/images/GitHub run blocked H3/H5/H7/H9. | P4-01 | CORE | BLOCKED |
| P4-03 | DEVOPS | Metrics endpoint tests, Prometheus/Grafana configs and five-panel JSON static checks pass. Live scraped targets/panels blocked H5/H10. | P4-02 | CORE | BLOCKED |
| P4-04 | DEVOPS | Tag-triggered GHCR workflow statically parsed with packages:write; build/publish validation blocked H5/H9. | P4-03 | CORE | BLOCKED |
| M4 | DEVOPS | LIVE TCP e2e script implemented; stack startup/targets/browser gate blocked H5/H7/H10. | P4-04 | CORE | BLOCKED |
| P5-01 | ML | Decision-based metrics/safety-floor and provenance/leakage guards tested; ablation/error/latency harness executed on explicitly SMOKE data; no superiority claim. | M4 | CORE | DONE |
| P5-02 | ML | Harness and pending-status evaluation docs exist. Real threshold/error/latency interpretation blocked on trained data/artifact H8. | P5-01 | CORE | BLOCKED |
| P5-03 | DOCS | README, model card, per-topic pending evaluation docs, report outline/drafts, diagrams, viva/demo instructions and objective gaps written; status/fixture/notebook checks passed. | P5-02 | CORE | DONE |
| P5-04 | BE | Honest security matrix complete; key controls tested. Audit/native/container/browser security evidence blocked H3/H4/H5/H7. | P5-03 | CORE | BLOCKED |
| M5 | DOCS | Full definition of done not satisfied; no trained research claim or production deployment claim. Complete H1/H3-H10 and all gates first. | P5-04 | CORE | BLOCKED |
| P4-05 | DEVOPS | STRETCH intentionally deferred until every CORE task and gate is verified. | M5 | STRETCH | TODO |
