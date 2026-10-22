# Latency

**PENDING: requires trained model artifact**

The harness measures per-sample local inference plus static analysis, including enabled attributions. It records observed p50/p95 and excludes HTTP/DB. Operational API/model histograms are separate. SMOKE latency is machine-specific pipeline evidence only and does not estimate CodeBERT production latency. The brief target of about a minute per PR is a target, not a measured result.

Exact command after training:

```bash
python -m ml.evaluation_run --artifact models/codesentinel-codebert/v1 --test ml/data/processed/test.jsonl --validation ml/data/processed/validation.jsonl --output docs/evaluation/trained-results.json
```

First prepare data and train: `python -m ml.data.download`, `python -m ml.data.split`, `python -m ml.train --config ml/configs/train_codebert.yaml`. Real C static analysis requires cppcheck. No benchmark superiority claim is inferred automatically.
