# Error analysis

**PENDING: requires trained model artifact**

The harness records false-positive/false-negative sample hashes, labels, decisions and risk without source. A researcher must manually categorize semantic root causes after full training. There is no fabricated error taxonomy or error count. Near duplicates, truncated context and domain shift are limitations, not measured causal conclusions.

Exact command after training:

```bash
python -m ml.evaluation_run --artifact models/codesentinel-codebert/v1 --test ml/data/processed/test.jsonl --validation ml/data/processed/validation.jsonl --output docs/evaluation/trained-results.json
```

First prepare data and train: `python -m ml.data.download`, `python -m ml.data.split`, `python -m ml.train --config ml/configs/train_codebert.yaml`. Real C static analysis requires cppcheck. No benchmark superiority claim is inferred automatically.
