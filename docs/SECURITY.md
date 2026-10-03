# Prototype security notes

- Gemini and risk-engine credentials are read only by server routes. No secret uses a `NEXT_PUBLIC_` prefix.
- Incoming payment, conversation, employee-action, and model payloads are schema validated.
- External service calls have hard timeouts and fail safely.
- The AI can recommend escalation but has no tool that releases, cancels, freezes, or permanently denies funds.
- Customer conversation is opt-in and limited to the intervention. The prototype does not access SMS, email, calls, WhatsApp, or social media.
- Employee/customer identities are fictional. The profile switch is a local demo-role fallback, **not production authentication**. A production deployment must enforce Auth0 roles and MFA at the edge/server before exposing financial data.
- Demo state is process memory and resets on restart. It is not suitable for real financial or personal data.

## Known prototype boundaries

These are deliberate hackathon trade-offs, listed so nobody mistakes them for production posture:

- **The browser supplies its own behavioral inputs.** `components/payment-form.tsx` sends `customerId`, `deviceId`, and `region` in the request body, which are exactly the fields the risk engine trusts. A real deployment must derive device and location server-side from the session, device attestation, and request metadata, never from the client.
- **The headless API is open by default.** `GUARDIAN_API_KEY` unset means `authorizeGuardianRequest` allows every request, and `GUARDIAN_ALLOWED_ORIGIN` unset means CORS `*`. Correct for a local demo; both must be set before the API is exposed.
- **`POST /api/demo/reset` is unauthenticated** and wipes all demo state. It must be removed or protected before any shared deployment.
- **No rate limiting, CSRF protection, or audit persistence.** Employee decisions are appended to in-process case notes, not an append-only log.
- **Trust approval is simulated.** `POST /api/recipients/:id/trust-decision` accepts `secondFactorVerified` as an assertion rather than verifying a real second factor. The security property that matters here still holds: the customer-facing route can only reach `TRUST_REQUESTED`, so trust cannot be self-granted to escape an intervention.

## Agent authority

The agent can pause a payment, release the pause it created itself, and recommend human review. `INTERVIEW_OUTCOMES` in `lib/guardian/service.ts` is the exhaustive list, and it contains no cancel, deny, freeze, or law-enforcement outcome. `CANCELLED` is reachable only via `applyHumanDecision`, asserted by a test.
