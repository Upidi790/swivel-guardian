# Recall improvement experiments

The optional candidate endpoint is `POST /ml/candidate/analyze`. The existing
`/ml/analyze` remains version 3. Read the [selected candidate results](ml_artifacts/recall-selected/RESULTS.md)
before deciding how to use the experiment. These are retrospective results on
the same chronological test period used previously, not a fresh independent test.

## What changed

- Restored all 339 anonymized V-features. The older filter stopped after 80,
  excluding everything after V123.
- Compared ordinary and fraud-weighted LightGBM models with more capacity.
- Explicitly selected AUC for early stopping, avoiding implicit default metrics.
- Tested transaction amount cents, relative hour, elapsed-time anchors, and
  anonymous card/address/time combinations. These are not verified identities.
- Selected the candidate with the lowest validation false-positive rate at
  at least 90% validation recall. Evaluated fixed thresholds on the later test.

The subsequent [balancing comparison](ml_artifacts/balance-v6/RESULTS.md) adds
equal class influence, 4:1 legitimate/fraud undersampling, and recency weighting.
All real training fraud examples are retained. No synthetic transactions are
inserted into the source database or evaluation sets.

The timing features use only the current transaction. Tests verify that changing
future transactions or labels does not change those features. Category dictionaries
are fitted only on training rows. Interview answers and outcome labels are excluded
from model requests.

## Call the candidate locally

From this project folder, start the server:

```powershell
.\.venv\Scripts\python.exe api.py
```

In a second PowerShell terminal in the same folder:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/ml/candidate/analyze -Method Post -ContentType 'application/json' -InFile ml_artifacts/recall-selected/high_score-request.json
```

Use the generated example's exact feature schema. Extra fields such as `isFraud`
are rejected; missing source values can be explicit nulls. The timing model also
requires `TransactionDT`, the source dataset's relative seconds, not a fabricated
calendar date.

The response separates two policies:

| Field | Meaning |
|---|---|
| `requires_intervention` | Balanced alert threshold chosen for maximum validation F1. |
| `screening_requires_interview` | Lower threshold targeting 95% validation recall; can create many false alarms. |
| `model_score` | Uncalibrated model output, not a verified probability of a scam. |
| `feature_contributions` | Model associations, not proof or causal explanations. |

Neither flag executes, holds, or releases a payment. The interview agent can consume
the screening flag alongside customer answers, but the combined system needs its
own labeled evaluation. Asking questions does not automatically fix model errors;
scams missed by the initial screening cannot be recovered by an agent that never
sees them.

## Tiger Data and verification

`verify_recall_candidate.py` registers the selected model in `ml_models`, publishes
88,581 test predictions in `ml_predictions`, checks the confusion counts against
the saved report, and tests the actual HTTP route with database persistence.
It also verifies stable retries and rejects changed requests using the same ID.
It preserves existing source data and previous models. Detailed verification is in
`ml_artifacts/recall-selected/integration-verification.json` after a successful run.

## What remains before real scam detection

IEEE-CIS is a payment-fraud benchmark with proprietary anonymized features. A real
bank integration must supply compatible features; nulling unavailable fields is
not a valid replacement. It does not establish performance on deceived customers
authorizing payments to scammers.

The [FCA APP synthetic dataset](https://www.fca.org.uk/firms/digital-sandbox/authorised-push-payment-synthetic-data)
is more aligned with that scenario. The [Digital Sandbox access process](https://www.fca.org.uk/firms/innovation/digital-sandbox)
requires an account and application. No FCA data was used in these experiments.

Before selecting a real intervention policy, evaluate both legitimate and scam
payments from the intended environment, include realistic interview answers, and
reserve a new chronological period that has never influenced model development.
