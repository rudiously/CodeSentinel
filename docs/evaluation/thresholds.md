# Threshold analysis

**PENDING: requires trained model artifact**

Temperature and classification threshold are selected only on validation. Risk defaults are .35 WARN and .65 BLOCK, weights .5/.5, bonus .1 at p>=.5 and severity>=.6. The evaluation command sweeps WARN thresholds on a disjoint validation set only; it never selects thresholds on test. Safety-floor decisions differ from score-only metrics in rare model_only edge cases and must be discussed.

Exact command after training:

```bash
python -m ml.evaluation_run --artifact models/codesentinel-codebert/v1 --test ml/data/processed/test.jsonl --validation ml/data/processed/validation.jsonl --output docs/evaluation/trained-results.json
```

First prepare data and train: `python -m ml.data.download`, `python -m ml.data.split`, `python -m ml.train --config ml/configs/train_codebert.yaml`. Real C static analysis requires cppcheck. No benchmark superiority claim is inferred automatically.
