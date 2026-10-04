# Behavioral Risk Engine with customer history

The new endpoint is **POST /behavior/analyze**. It loads the customer's prior
Sparkov transactions from Tiger Data, builds behavioral features, and returns
baselines and investigation signals. The older IEEE-CIS routes remain separate.

Read [measured results](sparkov_artifacts/RESULTS.md) for fraud detection and
unusual-legitimate-payment evaluation. This is a synthetic demonstration, not a
production bank integration or a guarantee of scam prevention.

## Try it

From this folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe api.py
```

In another PowerShell terminal in the same folder:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/behavior/analyze -Method Post -ContentType 'application/json' -InFile sparkov_artifacts/high_score-request.json
```

Use `low_score-request.json` for a contrasting example. Saved responses are beside
these requests. Restart any server launched before this endpoint was added.

The request contains transaction_id, user_id, timestamp, amount, merchant_id,
category, home_latitude, home_longitude, merchant_latitude, and merchant_longitude.
Identifiers represent simulated source cards and merchants. Source timestamps
have no verified timezone; send them in the example's timezone-free ISO format.
Do not reinterpret coordinates as the customer's live position.

The response includes:

- `baseline`: prior 90-day median, p95, category median, and history counts.
- `features`: amount deviations, prior merchant counts, category familiarity,
  source-hour patterns, payment frequency, and merchant geography comparisons.
- `signals`: readable descriptions of baseline deviations. These are descriptive
  evidence, not exact attributions of the trained model's score.
- `requires_intervention`: true/false when at least 20 prior comparable source
  observations exist; null with `INSUFFICIENT_HISTORY` otherwise. Null requires
  an explicit fallback; it must not be interpreted as safe.
- `risk_score`: percentile of the selected model score among training examples,
  not the percentage chance that the user is being scammed.
- `unavailable_features`: unsupported original bank-transfer fields.

Bhargav's agent should use the baselines to ask contextual questions, such as why
an amount differs from the customer's usual payments. No emails, victim answers,
or fraud labels are included in this model request. The model does not contact
anyone or hold money.

## Data and causality

The downloaded source contains official training and test files. A reproducible
50-customer subset was selected independently of labels. All available observations
for those identifiers were retained. No real names, street addresses, birth dates,
or gender fields are used by the model or imported into Tiger Data.

Features are calculated before observing the current transaction. Every event at
the same timestamp is scored before any of that timestamp's events enter history.
Later test events may use earlier test transactions, as an online system would,
but never their fraud labels. Source payment-success status is unavailable, so
history consists of observed records without pretending they are settled payments.

The database stores `sparkov_users`, `sparkov_transactions`, `sparkov_outcomes`,
`sparkov_models`, and `sparkov_risk_events`. Outcomes are isolated for evaluation.
The scoring query only retrieves matching-user transactions strictly before the
requested time. Requests are audited; identical retries return the saved result,
and conflicting reuse of the same transaction ID/model version is rejected.

Scoring a new request does not add it to settled history. This implementation uses
the imported fixture history; a real bank would need a separate authenticated
transaction-ingestion process and a compatible time/location contract.

## Unsupported bank-transfer scenarios

`sparkov_artifacts/simulated-bank-scenarios.json` contains 50 routine, 20 unusual
legitimate, and 20 scam-like transfers, plus their explicitly simulated history.
These exercise the original rules in `engine.py`, including new recipients,
registration age, device changes, and IP-region changes. The victim context is
stored separately and never passed to the behavioral rules. The paired legitimate
and scam-like cases demonstrate why an interview is necessary. They do not measure
real-world scam detection.

## Reproduce and verify

```powershell
.\.venv\Scripts\python.exe build_sparkov.py --zip ..\..\work\sparkov.zip
.\.venv\Scripts\python.exe bank_scenarios.py
.\.venv\Scripts\python.exe report_sparkov.py
.\.venv\Scripts\python.exe -m unittest test_behavior
.\.venv\Scripts\python.exe publish_sparkov.py
```

Publishing preserves the previous IEEE and synthetic-demo tables. Successful
HTTP/database verification is recorded in `sparkov_artifacts/integration-verification.json`.
Local standalone scoring is also available through `SparkovService(persist=False)`.
