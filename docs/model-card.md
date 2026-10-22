# CodeSentinel model card

**Status: PENDING: requires trained model artifact**

The real-model configuration fine-tunes `microsoft/codebert-base` for C function-level SAFE/VULNERABLE classification. CodeBERT is existing work by Feng et al.; CodeSentinel does not invent its architecture. Devign is existing work by Zhou et al.; the verified dataset distribution is Google's CodeXGLUE defect-detection dataset derived from Devign. See ml/data/README.md for source and license notes.

Only SMOKE artifacts currently exist: tiny randomly initialized RoBERTa, character-modulo-256 tokenizer, synthetic snippets, 64-token context. They verify training/export/serving mechanics and are not pretrained CodeBERT or research results. Service mode `real` means an artifact is loaded, not that it is a validated trained model; artifact_kind=SMOKE remains mandatory. STUB is a deterministic heuristic with no learned weights.

Full-model training uses seeded stratified sample splits after exact normalized deduplication and conflict removal. Proposed counts 21,808/2,724/2,726 are not verified. Near-duplicates may remain; repositories are not held out. Full tokenizer max length 512; long functions truncate. Chunk-and-max is an unimplemented experiment. Class weighting and validation-F1 early stopping are configured. Validation-only temperature calibration and recall-oriented classification threshold precede test evaluation. Risk policy thresholds remain configurable defaults, not empirically optimized claims.

Earlier reported accuracy 64.09%, precision 60.40%, recall 63.34%, F1 61.83% are **earlier run, not reproduced**. Current trained-model metrics: **PENDING: requires trained model artifact**. Generate them with `python -m ml.train --config ml/configs/train_codebert.yaml`, then `python -m ml.evaluation_run --artifact models/codesentinel-codebert/v1 --test ml/data/processed/test.jsonl --validation ml/data/processed/validation.jsonl --output docs/evaluation/trained-results.json`.

Artifacts use TorchScript (not ONNX), with numerical parity checks, tokenizer files, SHA256 manifest, dataset hash, calibration, configuration, git identity (explicitly unavailable if git is blocked), and MLflow run/registry identity. All manifest-listed files are verified; extra files, unsafe paths, and mismatches are rejected. Hashes do not authenticate an attacker-controlled manifest; distribution and metadata must be trusted. SMOKE and TRAINED versions have separate registry names.

Integrated gradients approximate sensitivity of the class-logit difference to embeddings against a zero-embedding baseline. Signed token attributions map to one-based source lines. The default eight midpoint steps are coarse, incur inference overhead, and do not establish causality or identify a proven vulnerability. Legacy artifacts without attribution methods return an empty list. Set EXPLAIN_STEPS=0 to disable; no invented token importance.

Intended use: educational/research assistance and a configurable PR review signal. Not a guarantee of safety, a replacement for maintainers, or a validated scanner for non-C code. Python static rules are independently useful; learned-model performance on Python/C++ is unvalidated. False positives/negatives and distribution shifts are expected. Maintainers retain merge authority.
