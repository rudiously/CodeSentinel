# CodeSentinel: Complete Project Documentation

*Prepared as the project manager's document set. Items marked **(proposed)** are design decisions to be confirmed and tuned during implementation.*

---

## Document 1: Project Charter

**Title:** CodeSentinel: AI-Assisted CI/CD Vulnerability and Code-Quality Gatekeeper

**Summary:** CodeSentinel is a GitHub-integrated system that reviews every pull request before merge. It combines a fine-tuned CodeBERT vulnerability classifier, rule-based static analysis, and a risk engine that outputs a PASS, WARN, or BLOCK decision with human-readable reasons. The whole pipeline is tracked with MLflow, served through FastAPI, packaged in Docker, and automated through GitHub Actions.

**Owner:** Rudra (research, ML, MLOps, backend, CI/CD, evaluation, documentation, presentation, viva)

**Institution context:** B.Tech CSE (AI), Vishwakarma Institute of Technology, Pune

---

## Document 2: Problem Statement

Modern teams merge code many times a day. Security review does not scale with that pace.

1. **Rule-based tools only catch what they were told to catch.** Linters and pattern scanners detect known unsafe patterns but miss vulnerabilities that do not match a rule.
2. **Manual review is inconsistent.** Reviewers are busy, security expertise is uneven, and subtle flaws pass through.
3. **Findings arrive too late.** Vulnerabilities found after release cost far more to fix than ones caught at the pull request stage.
4. **Existing outputs are hard to act on.** Raw tool output is noisy and rarely explains why something matters or what to do.
5. **ML research does not reach developers.** Vulnerability-detection models are mostly evaluated in notebooks, not embedded into the workflow where decisions are made.

**Problem statement:** *Design and build an automated pull-request gatekeeper that combines a learned vulnerability signal with static analysis and an explainable risk decision, integrated directly into the CI/CD workflow, so that risky code is flagged before it is merged.*

---

## Document 3: Objectives

**Primary objective:** Deliver a working end-to-end system that scores pull requests for vulnerability risk and gates merges automatically.

**Specific objectives**

| ID | Objective | Measure of success |
|---|---|---|
| O1 | Train a vulnerability classifier on a cleaned public dataset | Reproducible fine-tuning; metrics logged in MLflow |
| O2 | Serve the model through an API | FastAPI endpoint returns probability and metadata |
| O3 | Add rule-based static analysis | Findings returned with severity and line numbers |
| O4 | Build a risk engine | Combined score maps to PASS, WARN, or BLOCK with reasons |
| O5 | Integrate with GitHub | PR triggers workflow, comment posted, check status set |
| O6 | Ensure reproducibility | One command starts the full system in Docker |
| O7 | Demonstrate value | Ablation shows combined system beats model-only and static-only |
| O8 | Provide visibility | Dashboard shows scans, decisions, and model history |
| O9 | Document and defend | Report, architecture diagrams, results, and viva preparation |

---

## Document 4: Scope

**In scope**
- Function-level binary classification (SAFE vs. VULNERABLE) using fine-tuned `microsoft/codebert-base`
- Static analysis integration (for example Bandit or Semgrep)
- Risk engine with PASS, WARN, BLOCK decisions and explanations
- FastAPI service, Docker packaging, GitHub Actions integration
- MLflow experiment tracking and model registry
- Dashboard (built last)
- Ablation, threshold, and error analysis

**Out of scope**
- Inventing a new model architecture or claiming to have invented CodeBERT or Devign
- Automatic code fixing or patch generation
- Guaranteeing detection of all vulnerabilities
- Production-scale multi-tenant deployment
- Kubernetes orchestration (optional stretch only)

---

## Document 5: Problems We Solve

| Problem | How CodeSentinel addresses it |
|---|---|
| Linters miss unknown patterns | A learned model contributes a second, independent signal |
| ML models stay in notebooks | The model is served by an API and called from CI |
| Late discovery of vulnerabilities | Checks run on every pull request, before merge |
| Noisy, unexplained alerts | Every decision includes reasons from both signals |
| Inconsistent reviews | The same automated gate applies to every PR |
| Hard-to-reproduce ML experiments | MLflow logs parameters, metrics, artifacts, and models |
| "Works on my machine" | Docker gives a reproducible runtime |
| Unclear trust in ML output | The model is one signal; the risk engine and static analysis cross-check it |

---

## Document 6: Uniqueness and Positioning

**What is genuinely distinctive**

1. **Integration over isolation.** The value is the full chain from model to merge decision, not a standalone classifier.
2. **Hybrid decisioning.** ML probability and static-analysis severity are combined in one explainable risk score. Agreement between signals raises confidence.
3. **Workflow-native.** The tool lives where developers already work (the pull request), as a check and a comment.
4. **Honest evaluation.** Duplicate removal and cross-split leakage removal lower headline numbers but make them trustworthy.
5. **Ablation-backed claims.** We measure whether combining signals actually helps, rather than assuming it.
6. **Full MLOps loop.** Tracking, registry, containerization, and CI are part of the deliverable.

**What we do not claim**
- A new ML algorithm
- State-of-the-art accuracy
- Replacement of human security review

**Comparison with existing approaches**

| Approach | Strength | Gap CodeSentinel addresses |
|---|---|---|
| Linters / pattern scanners | Fast, precise on known rules | No learned signal; miss novel patterns |
| Semantic analysis tools (such as CodeQL) | Deep, query-based analysis | Rule and query driven; needs expert-written queries |
| Commercial scanners | Mature, broad coverage | Closed, costly, hard to study or adapt |
| Research models (Devign, CodeBERT-based) | Learn from data | Rarely packaged into a CI workflow |
| **CodeSentinel** | Hybrid, explainable, workflow-integrated, reproducible | Smaller scale; model accuracy is moderate |

---

## Document 7: Requirements Specification

**Functional requirements**
- FR1: Accept code (functions or diffs) via an API and return a vulnerability probability.
- FR2: Run static analysis and return findings with severity and line numbers.
- FR3: Combine both into a risk score and a PASS, WARN, or BLOCK decision.
- FR4: Return a structured explanation for each decision.
- FR5: Trigger automatically on pull requests via GitHub Actions.
- FR6: Post a PR comment and set the check status.
- FR7: Log scan results for the dashboard.
- FR8: Allow the model version to be changed without code changes.

**Non-functional requirements**
- **Performance:** a typical PR scanned in about a minute or less (target, CPU acceptable)
- **Reproducibility:** fixed seeds, logged configs, containerized runtime
- **Reliability:** if the service fails, the workflow reports an error instead of silently passing
- **Security:** secrets only in GitHub secrets or environment variables, and no code stored beyond the necessary scan logs
- **Maintainability:** modular layout with ML, API, risk engine, and CI separated
- **Transparency:** every decision traceable to its inputs

---

## Document 8: System Architecture

**Flow**

1. A developer opens or updates a pull request.
2. GitHub Actions triggers the CodeSentinel workflow.
3. The workflow extracts changed files and splits them into functions.
4. It sends the functions to the FastAPI service.
5. In parallel, the service runs (a) CodeBERT inference and (b) static analysis.
6. The risk engine combines the outputs into a score and decision.
7. The service returns a structured report.
8. The workflow posts the comment and sets the check status.
9. The scan is logged for the dashboard.

**Components**

| Component | Responsibility |
|---|---|
| Data pipeline | Clean, deduplicate, remove leakage, split |
| Training module | Fine-tune CodeBERT, log to MLflow |
| Model service | Load model, run inference |
| Static analysis module | Run rule-based scanner, normalize findings |
| Risk engine | Fuse signals, apply thresholds, generate reasons |
| API layer (FastAPI) | Expose endpoints |
| GitHub Action | Orchestrate PR integration |
| Dashboard | Display scans and model history |
| Docker | Package the service |

---

## Document 9: Data and ML Methodology

**Dataset:** DetectVul/Devign, cleaned for duplicates and cross-split overlap.

**Splits:** Train 21,808, Validation 2,724, Test 2,726.

**Model:** `microsoft/codebert-base` fine-tuned for binary SAFE vs. VULNERABLE classification.

**Current held-out test results**

| Metric | Value |
|---|---|
| Accuracy | 64.09% |
| Precision | 60.40% |
| Recall | 63.34% |
| F1 | 61.83% |

**Interpretation:** Vulnerability detection on Devign is a hard and noisy benchmark, and results in this range are typical for plain fine-tuning. Cleaning for leakage keeps the numbers honest. This is why the model is positioned as a supporting signal.

**Planned improvements (stretch)**
- Class weighting or threshold tuning to favor recall
- Better handling of long functions (truncation vs. chunking)
- Comparison against GraphCodeBERT
- Calibration of output probabilities, since the risk engine depends on them

**Experiment tracking:** MLflow experiment `CodeSentinel-CodeBERT` logs parameters, metrics, artifacts, and the model. Model files are stored on Google Drive and then moved into the local project.

---

## Document 10: Risk Engine Design (proposed)

**Inputs**
- `p_model`: model vulnerability probability for the riskiest function (0 to 1)
- `s_static`: normalized static-analysis severity (0 to 1), where High maps to 1.0, Medium to 0.6, and Low to 0.3, taking the maximum finding

**Score (initial formula)**

`risk = w1 × p_model + w2 × s_static + bonus`

with starting weights around `w1 = 0.5` and `w2 = 0.5`, and an agreement bonus of about `0.1` when both signals are individually elevated.

**Decision thresholds (initial values, to be tuned on validation data)**
- `risk < 0.35` → PASS
- `0.35 ≤ risk < 0.65` → WARN
- `risk ≥ 0.65` → BLOCK

**Safety rule:** any high-severity static finding forces at least WARN, regardless of the model.

**Explanation output:** the engine lists which function, which finding, and which signal drove the decision.

All weights and thresholds are hyperparameters, selected on the validation set and reported in the threshold analysis.

---

## Document 11: API Design (proposed)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Service and model status |
| `POST /predict` | Code in, vulnerability probability out |
| `POST /analyze` | Static analysis findings |
| `POST /scan` | Full pipeline: model + static + risk decision + reasons |
| `GET /model/info` | Active model version and metrics |

**Sample `/scan` response (shape)**
- `decision`: PASS, WARN, or BLOCK
- `risk_score`: number
- `functions`: list with name, file, probability
- `findings`: list with rule, severity, line
- `reasons`: list of plain-language explanations

---

## Document 12: CI/CD Integration Plan

- **Trigger:** `pull_request` events.
- **Steps:** checkout, detect changed files, extract functions, call the service, parse the report, post the comment, set pass or fail.
- **Branch protection:** BLOCK fails the check and prevents merge; WARN passes with a comment.
- **Failure handling:** if the service is unreachable, the check reports an error rather than silently passing.
- **Secrets:** tokens stored in GitHub secrets.
- **Also in CI:** tests, lint, and a Docker build on every push.

---

## Document 13: Technology Stack

| Layer | Choice |
|---|---|
| Language | Python |
| ML | PyTorch, Hugging Face Transformers (CodeBERT) |
| Tracking | MLflow |
| Serving | FastAPI |
| Static analysis | Bandit and/or Semgrep |
| Packaging | Docker, docker-compose |
| CI/CD | GitHub Actions |
| Training environment | Google Colab, with models saved to Google Drive |
| Dev environment | VS Code |
| Frontend | Lightweight web dashboard |
| Optional | Kubernetes (stretch only) |

---

## Document 14: Project Plan

| Phase | Work | Deliverable |
|---|---|---|
| 1 | Retrain and save model permanently to Google Drive | Persistent model |
| 2 | Integrate model into VS Code project | Local inference script |
| 3 | FastAPI service | `/predict` and `/health` |
| 4 | Static analysis | `/analyze` with normalized findings |
| 5 | Risk engine | PASS, WARN, BLOCK with reasons |
| 6 | GitHub Actions | PR bot and check status |
| 7 | Docker | Containerized system |
| 8 | Dashboard | Scan and model views |
| 9 | Experiments and final evaluation | Ablation, thresholds, error analysis |
| 10 | Presentation and viva | Slides, demo, Q&A |

**Current status:** Phase 1. The earlier model and MLflow runs were lost to a Colab reset, so training is being rerun with permanent saving.

**Milestones:** M1 model persisted (Phase 1–2), M2 working API (Phase 3–5), M3 live PR bot (Phase 6–7), M4 evaluated and documented (Phase 8–10).

---

## Document 15: Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Model lost again | Medium | High | Save to Drive, back up locally, use MLflow registry |
| Moderate accuracy | High | Medium | Frame as supporting signal; show ablation; report limits |
| Function-level model vs. PR diffs | Medium | Medium | Extract functions from diffs; state the limitation |
| Dataset differs from real repos | High | Medium | Test on handcrafted vulnerable samples; discuss gap |
| Scope creep | High | High | Fixed priority order; Kubernetes and polish optional |
| False positives annoy users | Medium | Medium | Tune thresholds; WARN rather than BLOCK for uncertain cases |
| Single-person workload | High | High | Build in demoable increments; reserve time for Phases 9–10 |
| Service downtime | Low | Medium | Explicit error state in the workflow |

---

## Document 16: Testing and Evaluation Plan

**Testing**
- **Unit tests:** risk engine, function extraction, static-analysis parsing
- **API tests:** each endpoint with valid and invalid input
- **Integration test:** a sample PR end to end
- **Regression set:** a small collection of known-clean and known-vulnerable snippets

**Evaluation**
1. Model metrics on the clean test set (accuracy, precision, recall, F1, confusion matrix)
2. **Ablation:** model only vs. static only vs. combined
3. **Threshold analysis:** trade-off between false alarms and missed vulnerabilities
4. **Error analysis:** categories of code the model misclassifies
5. **Latency:** time per scan
6. **Demo scenarios:** one clean PR and one deliberately vulnerable PR

---

## Document 17: Security, Ethics, and Limitations

- **Not a guarantee.** CodeSentinel reduces risk; it cannot prove code is safe.
- **False positives and negatives exist.** Both are reported openly.
- **Data handling:** scanned code is processed transiently, and only minimal scan metadata is logged.
- **Dataset licensing and citation:** all datasets and models are credited.
- **Human in the loop:** BLOCK can be overridden by a maintainer, and WARN informs rather than decides.
- **Known limitation:** the model is trained on function-level C-style data, so performance on other languages is not established.

---

## Document 18: Deliverables Checklist

- Cleaned dataset and split description
- Fine-tuned model with MLflow history
- FastAPI service
- Static analysis module
- Risk engine
- GitHub Action and PR bot
- Dockerized system
- Dashboard
- Evaluation report (ablation, thresholds, error analysis)
- Final project report and architecture diagrams
- Presentation and demo script
- Viva Q&A notes

---

#

## Document 21: References to Cite

- Zhou et al., *Devign: Effective Vulnerability Identification by Learning Comprehensive Program Semantics via Graph Neural Networks* (NeurIPS 2019)
- Feng et al., *CodeBERT: A Pre-Trained Model for Programming and Natural Languages* (2020)
- Guo et al., *GraphCodeBERT: Pre-training Code Representations with Data Flow* (2021)
- Fan et al., *Big-Vul* dataset paper (MSR 2020)
- Documentation: MLflow, FastAPI, GitHub Actions, Bandit, Semgrep
