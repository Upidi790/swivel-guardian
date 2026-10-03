# Prototype security notes

- Gemini and risk-engine credentials are read only by server routes. No secret uses a `NEXT_PUBLIC_` prefix.
- Incoming payment, conversation, employee-action, and model payloads are schema validated.
- External service calls have hard timeouts and fail safely.
- The AI can recommend escalation but has no tool that releases, cancels, freezes, or permanently denies funds.
- Customer conversation is opt-in and limited to the intervention. The prototype does not access SMS, email, calls, WhatsApp, or social media.
- Employee/customer identities are fictional. The profile switch is a local demo-role fallback, **not production authentication**. A production deployment must enforce Auth0 roles and MFA at the edge/server before exposing financial data.
- Demo state is process memory and resets on restart. It is not suitable for real financial or personal data.
