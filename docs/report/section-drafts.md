# Report section drafts

## Introduction and problem
CodeSentinel assists pull request security review by combining a learned function-level vulnerability signal with static findings. It returns a traceable risk decision and integrates it into GitHub review. The problem addressed is moving reproducible research signals into a workflow where maintainers can inspect and act on them.

## Related work and contribution
CodeBERT (Feng et al., 2020), Devign (Zhou et al., NeurIPS 2019) and GraphCodeBERT (Guo et al., 2021) are existing work. The contribution here is integration: model serving, independent static analysis, a transparent configurable risk policy, automated PR gating, provenance and MLOps. There is no new network architecture or state-of-the-art claim. Semantic tools and commercial scanners have different breadth and maturity.

## Data and model methodology
The source identity is CodeXGLUE's Devign-derived defect-detection dataset. Raw download revision, source and date are recorded at runtime. Conservative exact normalization and deduplication precede stratified sample splits; conflicting labels are excluded. This does not remove all clones or establish held-out-repository generalization. Actual data counts remain pending. The full training config uses microsoft/codebert-base, weighted loss, early stopping and a 512-token truncation policy. Calibration and recall-oriented thresholds use validation only.

## System implementation
The model service implements Contract C independently. The backend parses complete source, optionally filters functions using unified-diff changed lines, obtains model and static signals, scores risk and persists metadata. Service failures yield ERROR. A primary GitHub Action fetches complete Git blobs without executing changed code, calls /scan, comments and fails BLOCK/ERROR. The signed webhook/App path also posts checks. A React dashboard presents history, findings, analytics and model provenance. Frontend source is written but npm-dependent build/browser checks are blocked.

## Decision framework
The scan-level combined score uses the highest function model probability and maximum static severity across the scan: .5p + .5s + .1 agreement bonus when p>=.5 and s>=.6, clamped at one. Static severity is the maximum of High=1, Medium=.6 and Low=.3. PASS is below .35, WARN below .65, otherwise BLOCK. A High finding forces at least WARN. Thresholds are configurable initial policy values; they are not claimed to have been optimized empirically. Unavailable analysis never produces PASS.

## Evaluation and results
PENDING: requires trained model artifact

Only synthetic SMOKE training, TorchScript parity and local integration have been measured. The model service loads a SMOKE artifact with explicit provenance and rejects tampering. Earlier model metrics are earlier run, not reproduced. The complete ablation/error/latency harness has been exercised on SMOKE, but it provides no evidence of real-model superiority. See evaluation docs for exact commands and measured smoke-results.json.

## Security, ethics and limitations
PR code is untrusted data and is never imported or executed. Webhook signatures precede JSON parsing. Inputs, subprocess time, output and paths are bounded; model hashes are checked and authenticated metadata APIs require JWTs by default. Source and attribution token text are removed from stored history. Hashes alone do not authenticate distribution. Deduplication and rate limiting are single-process; dependency audits, Docker runtime, native static tools and frontend verification remain blocked. Learned non-C performance is unvalidated, and human review is essential.

## Conclusion
The implemented local components establish a testable integration framework. Completing dataset training, native-tool verification, frontend checks and live GitHub/deployment evidence is necessary before declaring the full project complete. A favorable ablation outcome is not assumed.
