# Start here: Behavioral Risk Engine handoff

**PRIVATE TEAM PACKAGE:** the accompanying private ZIP includes the working `.env`
database credentials, as authorized by the project owner. Share it directly with
the teammate. Keep `.env` in the backend directory, outside source control and
frontend/browser bundles. Never use `NEXT_PUBLIC_`, `VITE_`, or other public-client
environment variables for these credentials. The frontend calls the backend API;
only the backend connects to Tiger Data.

This package is the transaction-analysis component for the Swivel demo. Your agent
calls it to obtain customer-history deviations, then asks the user questions to
investigate context. It does not interview users, execute payments, hold funds,
or send notifications.

## 1. Run on your computer

Use **Python 3.12**, matching the environment used to save the scikit-learn models.
Extract the ZIP and open a terminal inside `behavioral-risk-engine`.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ml-lock.txt
.\.venv\Scripts\python.exe -m unittest test_behavior
.\.venv\Scripts\python.exe api.py
```

macOS/Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-ml-lock.txt
.venv/bin/python -m unittest test_behavior
.venv/bin/python api.py
```

The server listens at `http://127.0.0.1:8000`. The trained model and synthetic
history are included, so **no retraining or Kaggle download is needed**. The included
`.env` enables the existing Tiger Data connection; the database is already populated.
Unrelated `DATABASE_URL`, `PGHOST`, or `TIMESCALE_SERVICE_URL` environment variables
can override the packaged configuration and should be cleared for this demo.
For an entirely offline smoke test, temporarily rename `.env` and ensure those
environment variables are unset. The service then uses the included local history.

The lock file records the tested versions. Use a supported Python/platform for
those packages. Load the included joblib models only from this trusted handoff;
joblib/pickle files can execute code when loaded.

## 2. Make the first call

In another PowerShell terminal:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/behavior/analyze -Method Post -ContentType 'application/json' -InFile sparkov_artifacts/high_score-request.json
```

For macOS/Linux:

```bash
curl --fail-with-body http://127.0.0.1:8000/behavior/analyze -H 'Content-Type: application/json' --data-binary @sparkov_artifacts/high_score-request.json
```

Try `low_score-request.json` next. Saved expected responses are included for
comparison. Database mode returns `persisted: true`; offline mode returns false.

Use the fixture's user IDs and source dates for this demo. Setting a request to
today while leaving its history in 2019–2020 creates an empty 90-day baseline.
New users also lack history. Arbitrary production payments are not compatible
until ingestion, identity mapping, and source-field contracts are implemented.

## 3. Connect your agent

Register an agent tool such as `analyze_payment(transaction)`. Its implementation
should make the HTTP call from your backend, then return the JSON to the agent.

```python
import json
from urllib.request import Request, urlopen

def analyze_payment(transaction):
    request = Request(
        'http://127.0.0.1:8000/behavior/analyze',
        data=json.dumps(transaction, allow_nan=False).encode(),
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)
```

Let HTTP/time-out errors propagate to an explicit unavailable-service fallback;
never turn an error into a low-risk result. The code uses Python's standard library.

### Request schema

Send exactly these fields; the complete examples are authoritative:

| Field | Type / meaning |
|---|---|
| transaction_id | Nonempty string; stable across retries. |
| user_id | Simulated card/customer identifier from the fixture. |
| timestamp | ISO source-clock time with no timezone, e.g. `2020-07-01T12:00:00`. |
| amount | Positive finite number, in the source dataset's amount units. |
| merchant_id | Simulated merchant identifier. |
| category | Purchase-category string. |
| home_latitude, home_longitude | Synthetic source home coordinates. |
| merchant_latitude, merchant_longitude | Synthetic source merchant coordinates; not live user location. |

Extra fields—including `is_fraud` and interview answers—are rejected. Keep victim
answers in your agent's conversation state, outside the transaction-model input.

### How to interpret the response

- `requires_intervention: true`: investigate with the user; this is not proof of a scam.
- `requires_intervention: false`: no model trigger; this is not payment authorization or proof of safety.
- `requires_intervention: null` and `decision: INSUFFICIENT_HISTORY`: fewer than 20
  prior 90-day observations; use an explicit fallback instead of treating null as false.
- `baseline`, `features`, and `signals`: use these for grounded questions. Signals
  are descriptive deviations, not exact explanations of every model decision.
- `risk_score`: a training-reference score percentile, **not a fraud probability**.
- `model_score` / `model_threshold`: internal selected-model operating point.
- `unavailable_features`: do not invent missing device, IP, recipient, or account data.

An appropriate question is: “This amount is above your usual range and this
merchant is unfamiliar. What is the payment for, and did anyone ask you to make it?”
Your agent then evaluates the user's explanation, pressure, secrecy, and impersonation.
It should not repeat internal scoring metadata as a confident accusation.

HTTP 400 means invalid input or a conflicting persisted retry. HTTP 503 means the
service failed; it is not a fraud verdict. The health endpoint reports that the
process runs, not that database connectivity has been verified.

## 4. Two distinct demo modes

| Endpoint | Intended use |
|---|---|
| `/behavior/analyze` | Current Sparkov customer-history ML demo: merchant purchases, personal amounts, categories, times, and merchant geography. |
| `/analyze` | Original explicitly simulated bank-transfer rules: recipient, recipient-registration age, device, and IP region. Use `example-request.json`; its fixture is `data.json`. |

Do not rename a merchant to a bank payee and claim equivalent evidence. Device/IP
and bank-recipient scenarios are in `sparkov_artifacts/simulated-bank-scenarios.json`.
The victim context there is deliberately withheld from the rules engine.

Historical IEEE-CIS experiment code is included for reference, but its large
model artifacts are not included. Do not use `/ml/*` routes for this handoff.
The existing `/ml/analyze` route is not an alias for the new behavioral engine.

## 5. Tiger Data integration

The private ZIP includes `.env`, so your backend can connect to the existing demo
database without copying secrets into application code. No reimport is necessary
for that database. If moving to your own PostgreSQL/Tiger instance, use
`.env.example` to configure its credentials, then run:

```powershell
.\.venv\Scripts\python.exe publish_sparkov.py
```

That creates/imports separate `sparkov_*` tables and verifies real HTTP/database
scoring. It does not require dropping existing data. Scoring queries only earlier
records for the matching user. Evaluation labels live in a separate table and are
not queried by the scoring path. Repeated identical requests return their audit
record; conflicting reuse of an ID/model version is rejected.

Scoring does not add the requested payment to settled history. The packaged
history is a demo fixture; real transaction ingestion is a separate integration.
The `/analyze` bank-rules route needs its own original schema/data if using database
mode; `publish_sparkov.py` initializes only the new Sparkov component.

## 6. Hosting boundary

`localhost` is local to the process calling it. A teammate's laptop or a cloud-hosted
agent cannot reach this service through their own `localhost`. For a first demo,
run the agent backend and this service on the same machine. A deployed integration
needs an authenticated backend deployment, TLS, and appropriate database access.
This loopback demo server is not a public deployment.

## 7. What has been verified, and what has not

- 44 project tests passed at handoff, including prior-only history, same-time
  exclusion, cross-customer isolation, category baselines, and label rejection.
- Actual HTTP scoring matched offline predictions with Tiger persistence and retries.
- The selected Sparkov test has 27,727 payments, including only 93 fraud labels:
  73 caught, 20 missed, 375 false alarms, 27,259 legitimate payments unflagged.
- Recall 78.5%, precision 16.3%, legitimate-payment false-positive rate 1.36%.
- These are synthetic, 50-customer subset results; the test was inspected during
  development. They do not establish 90% real-scam recall or production readiness.

Read `sparkov_artifacts/RESULTS.md` for the complete evaluation and
`SPARKOV-GUIDE.md` for implementation details. Keep this caveat in the team demo.

## 8. Files to start with

1. This document.
2. `sparkov_artifacts/high_score-request.json` and `high_score-response.json`.
3. `sparkov_artifacts/low_score-request.json` and `low_score-response.json`.
4. `api.py`, `sparkov_service.py`, and `behavior_features.py`.
5. `schema-sparkov.sql` if connecting to Tiger Data.

The included trained model and history are in `sparkov_artifacts/model.joblib` and
`history.joblib`. `MANIFEST.json` records the SHA256 of every packaged input file.
The full source dataset archive and `.venv` are excluded. To rebuild, download the
source linked in RESULTS.md and run `build_sparkov.py --zip <downloaded ZIP path>`.
