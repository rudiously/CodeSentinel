# Viva preparation

## Whole system
- **What is the contribution?** Reproducible integration and an explainable decision framework: learned signal + static rules + PR gate + provenance/MLOps.
- **What does STUB mean?** A deterministic heuristic with no trained model. Never cite it as vulnerability-detection accuracy.
- **What does real/SMOKE mean?** Actual loaded neural artifact, but tiny random initialization and synthetic data; pipeline evidence only.
- **Can PASS guarantee safety?** No. Models and static rules have false negatives, truncated context and distribution limitations.

## ML role
- **Why CodeBERT?** Existing pretrained code representation; full config fine-tunes binary labels. The offline smoke does not download or fine-tune CodeBERT.
- **How avoid leakage?** Exact normalized deduplication, conflicting-label exclusion, seeded splits and disjoint hashes. Near duplicates/repository overlap remain limitations.
- **Where are thresholds tuned?** Calibration and classification threshold use validation only. Initial risk thresholds are documented defaults, not measured optimization.
- **What does attribution prove?** Integrated gradients measures approximate local sensitivity against a reference embedding; it is not a causal explanation or proof of a bug.
- **Where are previous metrics?** Lost earlier run, not reproduced. Do not present them as current results.

## Backend role
- **Why pure risk engine?** Deterministic policy independently tested at boundaries and safety/error cases.
- **What if the model is down?** ERROR with null risk and a failing gate; no silent PASS or fallback from corrupt artifact to stub.
- **Why full blobs with diffs?** Unified diff fragments omit function context. Parse complete post-change files, then optionally select changed functions.
- **How are scanners isolated?** Temporary fixed filenames, argv arrays, no shell, timeouts; scanned code is not executed.
- **Why no source in history?** Minimize proprietary-code retention; detail pages explain source unavailability and retain findings/line ranges.

## DevOps role
- **How reproduce?** Python 3.11 pinned dependencies, configs/seeds, artifact hashes, MLflow, Docker Compose and CI definitions. Pinned setup/live containers are still unverified here.
- **Why TorchScript rather than ONNX?** Supported alternative in the specification; local parity passes. No ONNX claim.
- **What do dashboards measure?** Operational latency, inference time, volume, errors and decision mix—not ML accuracy.
- **Which secrets?** JWT, OAuth, webhook/App, database and Grafana credentials; environment or GitHub secrets only.

## Frontend role
- **How distinguish evidence?** Persistent STUB/SMOKE/SYNTHETIC labels plus mode/version and explicit loading/empty/error states.
- **What is unverified?** npm installation, strict TypeScript build, tests and browser behavior. Code is not a verified deployment.

## References
Devign: Zhou et al. (2019); CodeBERT: Feng et al. (2020); GraphCodeBERT: Guo et al. (2021). Official docs: FastAPI, GitHub Actions/App APIs, MLflow, Bandit, cppcheck, tree-sitter. Source URLs appear in ml/data/README.md.
