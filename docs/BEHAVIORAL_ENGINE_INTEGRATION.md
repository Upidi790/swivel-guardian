# Teammate behavioral engine integration

Guardian can call the teammate-owned service server-to-server. The browser never receives Tiger Data credentials or calls the engine directly.

## Enable the compatible transfer endpoint

Run the teammate service locally, then set these non-secret values in `.env.local`:

```env
RISK_PROVIDER=remote
RISK_ENGINE_URL=http://127.0.0.1:8000
RISK_ENGINE_PATH=/analyze
RISK_FALLBACK_TO_MOCK=true
GUARDIAN_INTERVENTION_FLOOR_USD=100
# Demo only: maps the fictional Maria UI to a synthetic engine profile.
RISK_ENGINE_DEMO_USER_ID=user_020
```

Guardian sends the compatible bank-transfer schema to `POST /analyze`, including a stable transaction ID, customer ID, amount, transfer metadata, recipient first-seen timestamp, device ID, and synthetic region. It maps the response's score, baseline, and signals into the existing customer and employee views.

The included Tiger fixture does not contain Maria's application ID. `RISK_ENGINE_DEMO_USER_ID=user_020` is an explicit **demo-only** mapping to an included synthetic profile, so the live app can show the engine response. It must be removed when a real institution maps authenticated customer IDs to its own transaction-history records.

## Important model boundary

The teammate's validated `/behavior/analyze` endpoint is a Sparkov synthetic **merchant-card** model. It requires fixture customer IDs, source timestamps, categories, and synthetic merchant/home geography. It must not be used for Maria's arbitrary bank-transfer form values or presented as bank-payee evidence. It remains useful for separate fixture-backed model evaluation.

For the Guardian transfer demo, `/analyze` is the compatible synthetic bank-transfer endpoint. An alert means *investigate*, not fraud. The score is an anomaly/training percentile, not a fraud probability. Guardian keeps behavior evidence separate from the customer's voluntary explanation and requires a human employee for final release or cancellation.

## Customer convenience and failure behavior

The demo has a USD $100 intervention floor. Payments below it complete without opening a customer conversation, even if a new payee contributes anomaly signals. This is a product policy guardrail, not a claim about model safety.

If the local engine is unavailable or returns an incompatible result, Guardian uses the declared mock provider while marking the provider as `remote-fallback`. Set `RISK_FALLBACK_TO_MOCK=false` only when you want an engine outage to surface as an evaluation error during testing.

## What the user must run

The provided ZIP contains a private `.env` and trusted serialized model files. Do not copy its `.env` into this repository or expose it in a browser. Extract and run the service in its own directory, following the teammate handoff's Python 3.12 instructions. Then start this Next.js app separately.
