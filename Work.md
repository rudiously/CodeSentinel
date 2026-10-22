CodeSentinel: Team Work Distribution (4 Members)
1. Project Leadership and Integration
The project lead (Rudra, as agreed) is not a fifth team member. Project leadership is a cross-cutting responsibility layered on top of one assigned role.

The project lead will:
- Own the overall architecture, shared contracts, and final report.
- Run a weekly integration check.
- Lead the viva narrative and ensure every member can explain how their work connects to the rest of the system.
- Review the risk engine closely because it is a central part of CodeSentinel's contribution.
Recommended assignment: The lead should also take Person 1 (ML Engineer) because the CodeBERT fine-tuning and MLflow setup already exist. This avoids restarting the model work.
2. Shared Contracts
Agree on these contracts in Week 1, before parallel implementation begins. They allow each person to build independently without waiting for neighbouring components.
Contract A — Model Interface (Person 1 → Persons 2 and 3)
Single-function interface:
predict(code: str) -> {
    "probability": float,
    "label": "SAFE" | "VULNERABLE",
    "token_importance": [...]
}
Batch interface:
predict_batch(codes: list[str]) -> list[dict]
Requirements:
- The model artifact must be versioned.
- Export as ONNX or TorchScript if practical.
- Load the artifact from a path or model registry configured through an environment variable.
- Document input limits, preprocessing, output semantics, and model version.
Contract B — Scan Report Schema (Person 2 → Person 4)
The scan report should include:
{
  "decision": "PASS",
  "risk_score": 0.0,
  "functions": [
    {
      "name": "example_function",
      "file": "src/example.c",
      "start_line": 1,
      "end_line": 10,
      "probability": 0.12
    }
  ],
  "findings": [
    {
      "rule": "example-rule",
      "severity": "LOW",
      "line": 5
    }
  ],
  "reasons": ["Example explanation"],
  "model_version": "codesentinel-model-v1",
  "timestamp": "2026-10-22T12:00:00Z"
}
The values above are illustrative examples, not actual scan results. Agree on the allowed values for decision (PASS, WARN, BLOCK) and severity levels before implementation.
Contract C — Model Service Endpoint (Person 3 ↔ Person 2)
The model container exposes:
- POST /predict
- GET /health
Define the request and response JSON formats, service port, error responses, and timeout behaviour before integration.
Mock-first rule
Until a real component is ready, build against a mock of the neighbouring contract:
- Person 2 uses a deterministic fake model that returns sample probabilities.
- Person 4 uses a hard-coded sample scan report.
- No one should block their work waiting for another component.
3. Person 1 — ML Engineer (Model Core)
Owns: the vulnerability model and its evaluation quality.
Workstream	Responsibilities
Data pipeline	Clean DetectVul/Devign data; check duplicates and cross-split leakage; retain the proposed split sizes of 21,808 / 2,724 / 2,726 only if they match the verified dataset and split procedure.
Training	Fine-tune microsoft/codebert-base for SAFE / VULNERABLE classification. Run GraphCodeBERT as a comparison only if time permits.
Improvements	Investigate class weighting, recall-oriented threshold selection, long-function handling, and probability calibration.
Explainability	Produce token-importance or other defensible explanations so the tool can identify code that contributed to a flag. Do not present attention weights as explanations unless their limitations are clearly stated.
MLflow	Use the CodeSentinel-CodeBERT experiment to track parameters, metrics, artifacts, and model versions/registry entries where supported.
Export	Produce a versioned ONNX or TorchScript artifact if supported by the model and deployment environment.
Evaluation	Report held-out test metrics, a confusion matrix, threshold behaviour, and error analysis.
Persistence	Save the model to durable storage (for example, Drive and a local backup); do not keep the only copy in Colab /content.


Deliverables
- Registered or versioned model artifact and evaluation report.
- predict() and predict_batch() implementations conforming to Contract A.
- Model card documenting training data, evaluation results, intended use, and limitations.
Reporting limitation
The current F1 score is approximately 61.8%, according to the project brief; verify it against the latest reproducible run before reporting it as a final result. The proposed split is described as held-out samples, not held-out repositories. State this limitation clearly, or create a repository-level split if reliable repository metadata is available.

Depends on: No other team member; start immediately.
Blocks: Final model integration for Persons 2 and 3.
4. Person 2 — Backend/API Engineer
Owns: API serving, static analysis, risk decisions, persistence, and GitHub integration.
Workstream	Responsibilities
FastAPI service	Implement /analyze-pr, /score-file, /history, and /health.
Static analysis	Wrap Bandit and/or Semgrep; normalize tool findings into a consistent schema and severity scale. Choose rules appropriate to the supported language and document tool limitations.
Risk engine	Combine model probability and static-analysis severity to produce PASS, WARN, or BLOCK, with human-readable reasons. Implement the agreed formula from Document 10 only after confirming its exact definition.
Database	Use PostgreSQL for repositories, PR scans, findings, and users/teams as required; manage schema changes with Alembic.
GitHub integration	Receive webhooks, fetch PR diffs, extract changed functions, call the model service, and post a PR comment/check status. Validate webhook signatures and handle retries safely.
Authentication	Implement GitHub OAuth or JWT according to the agreed deployment and security requirements.
Testing	Add pytest coverage for API routes, risk-engine rules, function extraction, and error cases.


Deliverables
- Dockerized FastAPI service with OpenAPI documentation.
- Working webhook flow against a test repository.
- Risk-engine unit tests, including boundary thresholds and missing/failed-analysis cases.
Depends on: Contract A; use a mock until Person 1's model is ready.
Blocks: Person 4's real-data integration.

Scope note: The risk engine is a central contribution. The project lead should review its formula, thresholds, edge cases, and tests rather than delegating it without oversight.
5. Person 3 — DevOps/MLOps Engineer
Owns: reproducible deployment, automation, model serving infrastructure, and operational monitoring.
Workstream	Responsibilities
CI/CD	Build GitHub Actions workflows for tests, Docker image builds, image publishing, and deployment.
Containers	Package the model server separately from the backend so each can be configured and scaled independently.
Local orchestration	Create a docker-compose.yml for the backend, model server, PostgreSQL, and frontend.
Monitoring	Configure Prometheus and Grafana for API latency, inference time, scan volume, and error rates where time permits.
Deployment	Deploy to an agreed environment such as a cloud VM, Render, Railway, or AWS. Verify current pricing and free-tier limits before choosing.
Reproducibility	Maintain environment configuration, secrets handling, health checks, and one-command local startup instructions.


Deliverables
- docker compose up starts the agreed local stack.
- Passing CI pipeline.
- Live Grafana dashboard if monitoring is in the final deployment scope.
Depends on: Contract C and initial containers from teammates; mocks are acceptable early.
Blocks: Final deployment.

Scope note: Kubernetes manifests are a stretch goal, not a prerequisite for the core system.
6. Person 4 — Frontend Engineer
Owns: the user-facing dashboard and demo experience.
Workstream	Responsibilities
Authentication	Build GitHub OAuth login and repository-connection screens, coordinated with the backend authentication flow.
Repository list	Show connected repositories and their latest scan status.
Scan history	Show per-PR scan history with PASS, WARN, and BLOCK indicators.
Findings view	Display flagged code lines, severity, and explanation reasons.
Analytics	Visualize vulnerability and risk trends per repository over time using Recharts or an equivalent chart library.
Model page	Display the current model version, evaluation metrics, and a link to MLflow if accessible.
UX polish	Provide consistent styling, loading and empty states, error handling, and responsive layouts.


Deliverables
- Deployed React application (Vercel or Netlify).
- Screenshots and a short demo video.
Depends on: Contract B; start with mock JSON from Day 1.
Blocks: Nothing technical, but the frontend is important to the final demonstration.
7. How the Components Connect
Person 4 — React dashboard
        │ REST API (Contract B)
        ▼
Person 2 — FastAPI, risk engine, static analysis,
           PostgreSQL, GitHub webhook
        │ HTTP (Contract C)
        ▼
Model server container ◄── Person 1's versioned model artifact (Contract A)
        ▲
        │ Packaged and operated by Person 3

Person 3 wraps the system with Docker Compose, CI/CD,
deployment, and monitoring.
8. Suggested Timeline
Adjust this plan to the actual project deadline. “Week 1” means the first week of implementation.
Phase	Person 1 — ML	Person 2 — Backend	Person 3 — MLOps	Person 4 — Frontend
Week 1: Foundations	Verify dataset, reproduce baseline, save model durably, configure MLflow.	Create repository structure, FastAPI skeleton, and initial DB schema.	Establish repo conventions, CI skeleton, and Docker Compose shell.	Create wireframes, React scaffold, and mock data.
Week 2: Core build	Improve model, evaluate thresholds, export artifact if practical, implement prediction interface.	Implement static analysis, risk engine v1, and mock-model integration.	Build model-server container and add PostgreSQL to Compose.	Build repository list, scan history, and findings views using mock data.
Week 3: Integration	Add explainability output, version/register model, complete evaluation report.	Connect real model, test webhook, and implement agreed authentication.	Complete local stack, CI image build/deployment, and initial Prometheus metrics.	Connect to real API, complete OAuth flow, and add analytics.
Week 4: Hardening	Run error analysis, ablation experiments if feasible, and finalize model card.	Expand tests, review thresholds with Person 1, and fix webhook/API edge cases.	Complete Grafana dashboards and cloud deployment.	Polish UX, record demo video, and capture screenshots.
Final phase	Prepare ML viva and explain limitations.	Prepare backend, static-analysis, and risk-engine viva.	Prepare MLOps, CI/CD, and deployment viva.	Rehearse the end-to-end demo and prepare frontend viva.


9. Integration Milestones
The project lead should verify each milestone with a live demonstration.
1. M1 — End of Week 1: Contracts are agreed, and all four skeletons run locally.
2. M2 — End of Week 2: The API returns a complete scan report using a mock model, and the frontend renders it.
3. M3 — End of Week 3: A pull request in a test repository triggers the webhook, the model scores changed code, a comment/check is posted, and the dashboard displays the scan.
4. M4 — End of Week 4: The system is deployed, monitored to the agreed level, and evaluated.
If the actual deadline is shorter, preserve the milestone order and reduce stretch scope rather than delaying the first end-to-end integration.
10. Team Coordination Rules
- Contracts change by agreement: communicate changes to every team member before merging them.
- Weekly 30-minute integration check: each person demonstrates their component running.
- Keep the main branch runnable: work in feature branches and use pull requests for review.
- One shared README: Person 3 maintains setup and operational instructions; every contributor updates documentation for their component.
- Report ownership: each person writes their own report section and prepares to answer viva questions about it.
- No integration blockers: use mocks until neighbouring components are ready.
- Secrets stay out of Git: use environment variables or a secrets manager; never commit tokens, credentials, or .env files containing secrets.
11. Scope Control
Core — must ship	Stretch — only if on schedule
Vulnerability model, evaluation, MLflow tracking, and versioned artifact	GraphCodeBERT comparison
FastAPI backend	Multi-language support
Static analysis and tested risk engine	Team accounts and advanced roles
GitHub webhook and PR comment/check	Feedback loop from reviewer overrides
Docker and Docker Compose	Kubernetes manifests
Dashboard for scan history and findings	Advanced Prometheus/Grafana polish
Ablation/evaluation evidence appropriate to the time available	Additional model experiments


If time runs short, cut stretch items first. The suggested implementation order is:
1. Model baseline and reproducible evaluation.
2. API skeleton and shared contracts.
3. Static analysis and risk engine.
4. GitHub integration.
5. Docker and CI.
6. Frontend integration and polish.
7. Final evaluation, documentation, and demo.
The exact risk formula referred to as “Document 10” must be located and verified before implementation. If that document is unavailable, the team should agree on and document a provisional formula instead of claiming to follow an unseen specification.
12. Immediate Next Steps
1. Confirm the four team members and assign one person to each role.
2. Agree on Contracts A, B, and C, including request/response examples and error behaviour.
3. Verify the dataset split sizes and reproduce the reported baseline metrics.
4. Find Document 10 or formally approve a provisional risk formula.
5. Create mock model predictions and a sample scan report so frontend/backend work can begin in parallel.
6. Create the shared repository, branch rules, issue board, and README.
7. Set the first integration review date.
Open decisions
- Are all four roles staffed by four different people?
- What is the actual project deadline?
- Is Document 10 available, and what risk formula does it specify?
- Which language(s) will the MVP support?
- Where will the model artifact and deployed services be hosted?