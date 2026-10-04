# Behavioral Risk Engine

## Customer-history implementation

The original behavioral use case is now implemented with a reproducible Sparkov
subset and the `/behavior/analyze` endpoint. Start with
[SPARKOV-GUIDE.md](SPARKOV-GUIDE.md) and [its results](sparkov_artifacts/RESULTS.md).
This computes customer-specific past-only baselines and keeps unsupported
bank-transfer scenarios explicitly simulated. The IEEE-CIS experiments below
remain separate benchmarks.

## Current ML implementation

The latest recall experiments and optional `/ml/candidate/analyze` endpoint are
documented in [RECALL-GUIDE.md](RECALL-GUIDE.md). The existing default remains v3;
the candidate exposes both balanced and high-recall screening signals.

The training-only class-balancing comparison is in
[balancing results](ml_artifacts/balance-v6/RESULTS.md). It tests equal class loss,
majority undersampling, and recency weights while preserving the original
validation and test class distributions.

The improved version 3 comparison and default API are documented in
[BENCHMARK-GUIDE.md](BENCHMARK-GUIDE.md), with results in
[the comparison report](ml_artifacts/benchmark/RESULTS.md). It compares logistic
regression and two LightGBM variants; selection uses validation data. The older
guide below documents version 2 and its 16-field request format.

The IEEE-CIS model, dataset import, and `/ml/analyze` endpoint are described in
[ML-GUIDE.md](ML-GUIDE.md). Use that guide for the trained-model workflow. The
original `/analyze` route below remains the rules-based synthetic baseline.
The downloaded dataset has 590,540 labeled transactions; source features and
evaluation outcomes live in separate `ieee_*` tables in Tiger Data.

The original Tiger Data connection and synthetic import were subsequently verified
successfully. The setup notes below record the earlier prototype and its limits.

This is your team's behavioral component: it measures how unusual a proposed payment is and returns an explanation for Bhargav's investigation agent. It never executes, blocks, or releases a payment and never contacts a customer. It does not read inboxes or calls.

## What is the backend stack?

The backend is the service running behind the app. This demo uses **Python + a JSON HTTP API + PostgreSQL/Tiger Data**. Tiger Data is the database; `storage.py` is the adapter connecting the Python service to it. Bhargav can call the same API regardless of his frontend or agent language.

## Run locally (no database required)

From this folder, in PowerShell:

```powershell
python demo.py
python -m unittest -v
python api.py
```

In another terminal in this folder:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/analyze -Method Post -ContentType 'application/json' -InFile example-request.json
```

The server binds only to your computer. The local JSON mode reads the generated dataset and does not persist risk events. Stop the server with Ctrl+C.

## Connect Tiger Data

You can now save the downloaded Tiger Data configuration as `.env` in this folder.
Install `requirements.txt` first. Both `storage.py` and `api.py` load this file
automatically. The supplied `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`,
`PGPASSWORD`, and `PGSSLMODE` fields are supported, avoiding URL password
encoding issues. An explicit `DATABASE_URL` environment variable takes priority.
Keep `.env` private; it is excluded by the supplied `.gitignore`.

1. Create a dedicated demo service/database in Tiger Data and obtain its PostgreSQL connection string.
2. Install the database driver: `python -m pip install -r requirements.txt`.
3. Set `DATABASE_URL` in the terminal environment using your actual connection string; keep it out of source control and chat. Follow Tiger Data's TLS connection settings (including certificate verification where supplied).
4. Run `python storage.py` to create the schema and load the synthetic records.
5. Run `python api.py` in that environment. It selects Tiger Data when `DATABASE_URL` is present.
6. Send the same example request. Verify a row appears in `risk_events`.

`schema.sql` creates users, recipients, devices, a transaction hypertable, and risk events. `storage.py` reads past transactions with parameterized SQL, computes the rolling amount baseline, and saves the full explanation. A per-user lock serializes evaluations; repeating an id with the same request returns its saved result, while a changed request is rejected. All evaluations of a payment should retain its original request and id.

The schema expects the TimescaleDB extension and its `by_range` hypertable API, available on current Tiger Data services. A plain PostgreSQL installation can use the tables if the `create_hypertable` line is omitted. Schema initialization needs appropriate database privileges.

**Live Tiger Data integration has not been tested:** no connection was supplied. The importer currently loads the supplied dataset; production transaction ingestion and settlement updates need a bank event adapter. Existing seed records are preserved on conflict, not updated. The prototype fetches all earlier customer history for recipient/device checks; scale this with maintained profiles and bounded database aggregates before production.

## Handoff contract

`POST /analyze` accepts a transaction object, illustrated in `example-request.json`:

```json
{
  "transaction_id": "proposed_payment_001",
  "user_id": "user_000",
  "timestamp": "2026-10-03T18:00:00Z",
  "amount": 2000,
  "currency": "USD",
  "recipient_id": "new_recipient",
  "recipient_first_seen": "2026-10-03T17:58:00Z",
  "device_id": "user_000_phone",
  "ip_region": "San Antonio",
  "transaction_type": "transfer"
}
```

The response includes `risk_score`, `risk_level`, `requires_intervention`, `signals`, `features`, `baseline`, and `data_quality_warnings`. The caller must supply authenticated, server-derived customer and payment data in a real deployment. Do not trust browser claims of known devices or payee age. A 400 means invalid input or an id conflict; a 503 means unavailable analysis, requiring the caller's explicit fallback policy. `/health` checks process availability, not database connectivity.

Bhargav should use `requires_intervention` to initiate contextual questions. The returned score is an anomaly score, **not a probability of fraud**. LOW means no configured trigger, not proof of safety. Payment pausing must be enforced separately by an authorized bank payment service; a chatbot cannot guarantee a hold by saying one exists.

## Scoring and data boundaries

| Signal | Points |
|---|---:|
| No successful previous payment to recipient | 25 |
| Amount above customer's comparable 90-day p95 | 25 |
| New recipient added less than 30 minutes ago | 15 |
| Device absent from prior successful payments | 15 |
| Approximate region absent from prior successful payments | 10 |
| Attempt frequency above historical threshold | 10 |

Scores sum to at most 100. MEDIUM begins at 40 and HIGH at 65; both trigger investigation. These are illustrative, untuned thresholds. Recipient novelty and recent creation are correlated, intentionally cumulative demo signals that require calibration before deployment. Severity is the signal's points divided by 25; it is an explanatory weight, not model confidence.

Amount statistics use only earlier successful payments from the same user, currency, and transaction type. At least 20 comparable payments are required for amount scoring. Missing location/device information is unknown, not a risk-free observation. Recent unsuccessful attempts count toward frequency. A known or trusted recipient never automatically bypasses other checks. Customer age is not a score input. Time-of-day remains null until a customer timezone is supplied. Amounts use ordinary numeric inputs for the demo and NUMERIC storage; a production payment contract should specify integer minor units or exact decimal strings.

No email datasets were downloaded or used to train this engine. Scenario narratives are separate from model inputs. The phishing and complaint datasets in the brief are optional scenario research, not transaction features.

## Evaluation

The deterministic generator creates 30 customers, 3,000 historical payments, and 90 independent holdout scenarios. Holdouts are assessed against frozen histories and do not update each other's baselines.

| Scenario | Cases | Investigations |
|---|---:|---:|
| Normal payments | 50 | 0 |
| Unusual but legitimate payments | 20 | 20 |
| Scam-like payments | 20 | 15 |

The deliberately separable behavioral scenarios yield 35 true positives, 55 true negatives, and zero errors against the **unusual behavior** label. These hand-designed results do not estimate real-world accuracy. If incorrectly treated as a scam classifier, precision is 42.9%, recall 75%, and F1 54.5%: 20 legitimate payments trigger and five scam-like payments escape. This is why the downstream investigation exists. `evaluation.json` includes both views.

Eight tests passed: normal/unusual behavior, no future/current/other-customer baseline leakage, cold starts and missing values, invalid amounts, currency isolation, exclusion of scenario labels, attempt frequency, and HTTP success/error handling. Database behavior still needs integration testing against your service.

## Research answers for the team

**Does SWIVEL have an established-vendor list?** Its public [partner directory](https://www.getswivel.io/partnerships/) lists banking/software integration partners. I did not verify a consumer trusted-payee or approved-merchant directory/API. Those are different concepts. Ask SWIVEL whether institution-scoped payee records, verified recipient identifiers, first-seen timestamps, and merchant verification status are available. Never infer trust from a display name or logo.

**Can we use IP/location?** A backend can observe the connecting IP, and a geolocation provider can map it to an approximate region. Trusted proxy configuration matters. IP geolocation does not establish a person's exact location and VPNs/proxies can change the apparent region; see [MaxMind's accuracy explanation](https://www.maxmind.com/en/geoip/ip-geolocation-accuracy). The payer's IP also does not reveal the recipient's physical location. This demo uses explicitly synthetic regions; SWIVEL's exposure of IP/device fields to your team remains unverified. Precise device location requires a separate permission-based integration.

SWIVEL publicly describes [APIs, SDKs, integration, and unusual-activity monitoring](https://www.getswivel.io/payment-processing-software/), but that does not confirm a pre-execution hold/release endpoint or unrestricted outgoing person-to-person transfer support. Ask for supported rails, a sandbox, pre-submit risk hooks, hold/release authority, and available telemetry before promising a live integration.

The [FTC describes the “move money to protect it” scam](https://consumer.ftc.gov/consumer-alerts/2024/03/never-move-your-money-protect-it-thats-scam), which informs one synthetic scenario. [Tiger Data explains hypertables](https://www.tigerdata.com/docs/learn/hypertables/understand-hypertables), which motivate the transaction storage design. No current hackathon prize eligibility was verified.

## Demo boundary and next steps

This deliverable implements your assigned engine and adapter, not a mock SWIVEL frontend or Bhargav's conversation agent. Isolation Forest is deferred until the rules and database integration work end to end. Before exposing the service beyond localhost, add authentication, per-user authorization, deployment controls, database migrations, durable ingestion, monitoring, and a tested failure policy. Trusted-contact notifications require opt-in and verified contacts. The demo sends no real messages or payments.
