# Model comparison and improved API

**Verified result:** richer-feature LightGBM won on validation average precision.
On the fixed retrospective test it achieved 58.3% precision, 47.6% recall, and a
1.23% false-positive rate. Logistic regression achieved 40.3%, 48.3%, and 2.58%,
respectively. See `ml_artifacts/benchmark/RESULTS.md` for both threshold policies.

All 24 tests passed. The live database check matched all 88,581 selected-model
test predictions to the local confusion matrix. Persisted HTTP scoring, identical
retries, conflicting-id rejection, and the default route were verified. Version 3
is activated for new API processes; database usage after publication was 426 MiB.

This comparison tests logistic regression and LightGBM instead of assuming that
one algorithm is best. The earlier model used only 16 fields, a small tree budget,
and category truncation. The new experiment tests both model and feature changes.

## Experimental protocol

The original 590,540 labeled IEEE-CIS rows are sorted by relative transaction time.
The first 70% train the models. The next 7.5% are used for LightGBM early stopping.
The following 7.5% select the candidate and thresholds. The final 15% are the same
88,581-row retrospective test as before. Tied times remain in the same partition.

The test has already been inspected in earlier work. This is not a fresh external
test, and no reshuffling can make it one. Candidate selection uses average
precision on the selection partition, before new test metrics are computed.

Candidates:

1. Logistic regression with 175 fields, train-only clipping/scaling/imputation,
   and one-hot categorical encoding. Convergence is checked.
2. LightGBM with the original 16 fields, preserving training categorical values.
3. LightGBM with 175 fields, including C/D, selected V and identity features, plus
   three categorical interactions. These interactions are not customer identifiers.

V features are selected by an unsupervised redundancy filter on the first 5,000
training rows only. No validation/test labels influence that filter. All
preprocessors are fit on the training partition. Outcome, transaction id and
customer interview answers are excluded from predictive features.

Two operating policies are reported for every candidate:

- Maximum selection-set F1: balances precision and recall; this is the serving policy.
- Maximum selection recall subject to selection false-positive rate <=2%: comparison
  with the earlier alert budget. The actual test false-positive rate can differ.

`ml_artifacts/benchmark/comparison.json` records the winner and every candidate's
metrics under both policies. `winner-selection.json` records the decision before
test evaluation. Models are not retrained on validation/test labels after selection.

## Use the selected model

After verification, `/ml/analyze` serves the selected version 3 model. The explicit
route `/ml/v3/analyze` uses that same model. `/ml/v2/analyze` retains the old model
and its 16-field contract. `/analyze` remains the original rule-based demo.

Start the local server:

```powershell
.\.venv\Scripts\python.exe api.py
```

In a second terminal from this folder:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/ml/analyze -Method Post -ContentType 'application/json' -InFile ml_artifacts/benchmark/high_score-request.json | ConvertTo-Json -Depth 10
```

Use `low_score-request.json` for a lower-scoring example. Restart an already-running
API after changing model activation. Requests must provide exactly the selected
source feature schema, with explicit nulls where source values are missing.
Missing feature-provider integration must not silently turn into fabricated values.

The returned `model_score` is the raw model output on a 0–1 scale and `risk_score`
is 100 times that value. Neither is a calibrated probability of social engineering.
LightGBM explanations use its native TreeSHAP contributions to log odds. Logistic
regression uses exact linear contributions. Neither represents causation. The
response includes the base and total log odds so reconstruction can be verified.

## Database

Only selected-model test predictions and model metadata are added to Tiger Data.
Existing versions remain identifiable by `model_version`. The base
`ieee_transactions` table still contains the previously imported 16-field subset;
it does not contain all richer model features. Those are read from the original
ZIP during training, and complete request examples are saved locally. Do not try
to score version 3 from the old database feature subset alone.

`ml_risk_events` holds complete API requests and results for demo calls. Evaluation
labels remain isolated in `ieee_outcomes` and are never passed to the agent.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml-lock.txt
.\.venv\Scripts\python.exe benchmark_models.py --zip "$env:USERPROFILE\Downloads\ieee-fraud-detection.zip"
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe publish_benchmark.py
.\.venv\Scripts\python.exe verify_benchmark_api.py
```

The verification script activates version 3 only after database-backed HTTP tests
succeed. Training can take several minutes and uses several GiB of memory. A new
experiment must use a new model version; do not overwrite published version keys.

## What this establishes

This is a benchmark improvement on IEEE-CIS online-payment fraud. The additional
anonymized V/C/D/id features may be proprietary aggregates unavailable to your bank
app, and their pre-payment availability must be confirmed before real use. Their
names do not justify natural-language claims about a person's habits or intent.

No candidate here establishes performance on authorized push-payment scams. The
FCA dataset remains a separate follow-up aligned to that target. A stronger Kaggle
result does not remove the need for that validation, the interview agent, or a
bank's independent payment-control policy.
