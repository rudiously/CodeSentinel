# Ablation

**PENDING: requires trained model artifact**

The harness evaluates model_only, static_only and combined with the same frozen risk policy. Flagged means WARN or BLOCK; blocked-only metrics are also recorded. High safety floors can affect decisions in model_only if static findings are supplied. The numeric score ablation remains p-only, static-only or combined respectively. No claim that the combined approach wins is made; O7 is an experimental question. The SMOKE harness ran with builtin Python rules on synthetic snippets; smoke-results.json is labelled SMOKE and is not comparative research evidence.

Exact command after training:

```bash
python -m ml.evaluation_run --artifact models/codesentinel-codebert/v1 --test ml/data/processed/test.jsonl --validation ml/data/processed/validation.jsonl --output docs/evaluation/trained-results.json
```

First prepare data and train: `python -m ml.data.download`, `python -m ml.data.split`, `python -m ml.train --config ml/configs/train_codebert.yaml`. Real C static analysis requires cppcheck. No benchmark superiority claim is inferred automatically.

Correctness update: accuracy/precision/recall/F1/confusion matrices now use actual policy decisions, including the High safety floor. Raw-score PR curves explicitly declare their score-only basis; they do not encode discrete safety overrides. ERROR analyses are rejected, not scored as safe. Synthetic test or validation samples force SYNTHETIC labelling even if the artifact is TRAINED.
