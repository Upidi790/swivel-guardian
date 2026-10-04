# Trained transaction-risk model

**Historical version 2 guide.** Version 3 uses the richer model described in
`BENCHMARK-GUIDE.md`. Once activated, `/ml/analyze` serves version 3; use
`/ml/v2/analyze` for the 16-field requests in this document.

The project now trains a HistGradientBoostingClassifier on the user's downloaded
IEEE-CIS dataset and exposes a separate `POST /ml/analyze` API. This is supervised
transaction-fraud scoring. It is not a model trained to recognize authorized
push-payment scams or a personalized customer-behavior model.

## Data and training

- Source: the original Kaggle `ieee-fraud-detection.zip` supplied in Downloads.
- Join: `train_transaction.csv` left-joined to `train_identity.csv` on TransactionID.
- Size: 590,540 labeled transactions. Many transactions lack identity records.
- Split: 413,378 earlier rows for training, 88,581 for validation, and 88,581 later
  rows for testing. Equal TransactionDT values stay in the same partition.
- Original Kaggle test files are unlabeled and are not used for reported metrics.
- Sixteen inputs: amount, dist1/dist2, product code, anonymized card/address codes,
  email domains, and device type/info. No label, transaction id, conversation text,
  or synthetic customer id is a training feature.
- Categorical vocabularies and numeric reference values are fitted on training
  rows only. Missing values are distinct from rare/unseen categories. The 250 most
  frequent values per category are retained; other values share an OTHER code.
- Amount and distances use log1p; categorical codes are explicitly categorical.
- 150 boosting iterations, 15 leaves, no random early-stopping split. Parameters
  were fixed before evaluation, not tuned against test outcomes.
- Threshold maximizes validation recall subject to at most 2% validation false
  positives. The test period can have a different false-positive rate.

`ml_artifacts/evaluation.json` records exact metrics, partition boundaries,
parameters, source ZIP SHA-256, and library version. `requirements-ml-lock.txt`
records the working Windows/Python 3.12 environment.

Version 2 fixes a missing-category representation inconsistency found by a unit
test. Version 1 predictions are retained as historical records and must not be
mixed into current evaluation queries. This correction was based on a failing
preprocessing test, not selection for improved held-out accuracy.

## What Tiger Data contains

Verified version 2 results on the untouched 88,581-row test partition:

| Metric | Result |
|---|---:|
| Precision | 31.1% |
| Recall | 24.6% |
| False-positive rate | 1.96% |
| Average precision | 0.201 |
| ROC AUC | 0.782 |
| Correct fraud alerts | 757 |
| False alerts | 1,679 |
| Missed fraud labels | 2,326 |

This is an initial limited-feature benchmark: it misses most labeled fraud at the
chosen alert threshold. It is not sufficient evidence for deployment as a scam
prevention system. Fraud prevalence in the held-out set is 3.48%.

All 17 local tests pass. The live integration check confirmed 590,540 source rows,
88,581 predictions for version 2, exact agreement between database and local
confusion matrices, persisted HTTP results, stable retries, and conflicting-id
rejection. `ml_artifacts/database-verification.json` records the check. Two model
versions are retained, so an unfiltered predictions count is 177,162. Database
size after import was approximately 408 MiB.

| Table | Purpose |
|---|---|
| `ml_datasets` | Source name and file checksum |
| `ieee_transactions` | All labeled-source rows, selected features and relative time |
| `ieee_outcomes` | Ground-truth labels for offline evaluation only |
| `ml_models` | Model versions and evaluation reports |
| `ml_predictions` | Held-out predictions, keyed by model version |
| `ml_risk_events` | API requests and saved model explanations |

The original small synthetic demo remains in `users`, `transactions`, etc. It is
not part of IEEE model training. No source dataset values were converted into
fictional customers, real calendar timestamps, trusted recipients, or currencies.
IEEE TransactionDT is a relative offset, so these records use an ordinary
PostgreSQL table rather than inventing timestamps for a time hypertable.

Use `inspect-ml.sql` in Tiger Data's Data View to explore the new tables. Refresh
the table browser if the new tables are not visible. Evaluation labels are
stored separately and are never queried by the ML scoring service.

## Run the API

In PowerShell from this project directory:

```powershell
.\.venv\Scripts\python.exe api.py
```

In a second PowerShell terminal, from the same directory:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/ml/v2/analyze -Method Post -ContentType 'application/json' -InFile ml_artifacts/high_score-request.json | ConvertTo-Json -Depth 10
```

`ml_artifacts/low_score-request.json` is a second example. Both were selected by
model score from the held-out partition, without using their outcome labels.

The request has exactly three top-level fields:

```json
{
  "dataset": "ieee_cis",
  "transaction_id": "unique-payment-id",
  "features": {
    "TransactionAmt": 2000,
    "ProductCD": "W",
    "DeviceType": "mobile"
  }
}
```

This small example is valid but omits most inputs. Use the generated complete
examples for a representative benchmark demonstration. Amount must be a positive
number; categorical codes must be strings. ProductCD is required. Generic bank
transfer requests cannot simply be relabeled as IEEE transactions; establish
compatible features and validate that domain before deployment.

The response includes:

- `risk_score`: 100 times the model output, not the original rule-point score.
- `intervention_threshold`: the selected threshold on the same 0–100 scale.
- `requires_intervention` and `decision`: model-based triage only.
- `feature_sensitivities`: the five strongest one-feature reference-replacement
  effects, including observed and reference values.
- `missing_features`, `rare_or_unseen_categories`, and domain limitations.
- `persisted`: true only when the database-backed service successfully saves the result.

Feature sensitivities recompute the model after replacing one feature with a
training median or mode. They are not SHAP, causal findings, or proof that a
particular attribute is suspicious. Replacements may break correlations or create
unrealistic combinations; use the numerical changes as model diagnostics. The
agent must not translate anonymized card/address codes into invented identities,
locations, or customer histories.

With the local `.env` configuration, results persist in Tiger Data. Identical
retries return the saved result. Reusing an id and model version with changed
features is rejected. A model file is loaded once per API process; restart the
server after retraining. Load only locally trained joblib files.

## Bhargav's agent handoff

The agent consumes the ML response and separately collects the customer's answers
about unsolicited contact, urgency, secrecy, claimed authority, and instructions
to move money. It must not receive `isFraud` as an input: that is an evaluation
answer, not information available before a real payment.

A low score cannot clear a payment as safe. Bank policy may independently initiate
an interview or escalation. A high score supports investigation, not a conclusion
that the customer is being scammed. No code here holds funds, calls customers,
sends contact notifications, or implements Bhargav's conversation agent.

The API is a localhost demo without user authentication. Separate authenticated
bank authorization and a deployment security review are required before real use.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml-lock.txt
.\.venv\Scripts\python.exe train_ml.py --zip "$env:USERPROFILE\Downloads\ieee-fraud-detection.zip"
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe import_ml.py
```

For a new model version when source rows already exist, use
`import_ml.py --predictions-only`. The importer uses bulk COPY and a transaction.
Imports do not overwrite existing source rows or model-version keys. Bump the
model version when changing training logic or parameters. Do not treat an unchanged
version key as a mechanism for updating a model.

## FCA follow-up

The [FCA authorized push-payment dataset](https://www.fca.org.uk/firms/digital-sandbox/authorised-push-payment-synthetic-data)
is synthetic but better aligned to the team's bank-impersonation and socially
engineered transfer scenarios. It is accessed through the FCA Innovation/Digital
Sandbox platform. It has not been downloaded or used in this model. It needs its
own schema inspection, feature availability checks, temporal split, trained model,
and evaluation; combining its labels with IEEE labels would conflate different tasks.

Sources: [IEEE-CIS data description](https://www.kaggle.com/c/ieee-fraud-detection/data),
[scikit-learn histogram gradient boosting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html).
