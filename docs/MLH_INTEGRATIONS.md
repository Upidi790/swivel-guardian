# MLH Technology Integration Status

## Gemini — integrated, core

Guardian calls Gemini server-side for adaptive questioning, natural-language signal identification, uncertainty handling, structured assessment, and customer explanations. The response is constrained to a JSON schema and validated with Zod. If the key is missing, the network times out, or the response is malformed, Guardian uses a clearly labeled deterministic fallback.

Required for live use:

```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash-lite
```

No key is required to run the full deterministic demo.

## Voice — intentionally deferred

The intervention is intentionally text-first. Voice is not part of the current product flow, so no ElevenLabs credential, route, or browser speech fallback is required. This keeps the customer experience quiet, accessible, and dependable for the hackathon demo.

## Tiger Data — clean teammate boundary

Guardian does not access Tiger Data directly. The teammate's behavioral service may use Tiger Data for transaction history and anomaly features, then return the normalized risk contract documented in `RISK_ENGINE_INTEGRATION.md`. Set `RISK_PROVIDER=remote` to use it.

## Auth0 — adapter-ready local fallback, not live

The prototype intentionally uses a clearly labeled customer/employee demo-role switch so authentication cannot block the core demo. A live Auth0 tenant has not been connected because it requires tenant-specific domain, client ID, secret, callback URLs, and configured roles. Production integration must enforce `customer` and `employee` roles server-side and enable MFA.

## DigitalOcean — deployment-compatible, intentionally not provisioned

The project builds as a standard stateful Next.js Node service and documents all environment variables. No DigitalOcean account or public resource has been created. Before public deployment, replace the in-memory repositories with Postgres and protect the demo reset endpoint.

## Backboard — intentionally deferred

Backboard was not added because the provider-based case repository already defines the correct memory boundary, and adding a second persistence platform would not improve the core demonstration before the other integrations are live.

## Solana and GoDaddy — intentionally skipped

Neither technology strengthens the scam-intervention architecture at this stage. No blockchain or custom-domain claim is made.
