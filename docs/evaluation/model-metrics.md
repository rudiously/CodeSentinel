# Model metrics

**PENDING: requires trained model artifact**

Earlier values (accuracy 64.09%, precision 60.40%, recall 63.34%, F1 61.83%) are earlier run, not reproduced. No trained-model scores are currently available. Test evaluation is invoked after model selection and validation calibration freeze. Raw confusion matrix and precision-recall curve arrays are logged in evaluation.json and MLflow artifacts.

Exact command after training:

```bash
python -m ml.evaluation_run --artifact models/codesentinel-codebert/v1 --test ml/data/processed/test.jsonl --validation ml/data/processed/validation.jsonl --output docs/evaluation/trained-results.json
```

First prepare data and train: `python -m ml.data.download`, `python -m ml.data.split`, `python -m ml.train --config ml/configs/train_codebert.yaml`. Real C static analysis requires cppcheck. No benchmark superiority claim is inferred automatically.
