# Claude Code Handoff — SWIVEL Guardian

Copy the prompt below into Claude Code when continuing this project. Do **not** paste API keys, promo codes, or `.env.local` contents into the prompt.

```text
You are continuing the SWIVEL Guardian hackathon prototype in this repository:
C:\Users\rbha6\OneDrive\Documents\ChatGPT\SWIVEL project

First inspect `README.md`, `docs/GUARDIAN_INTEGRATION.md`, `docs/MLH_INTEGRATIONS.md`, `.env.example`, and `AGENTS.md` if present. Preserve any user changes; the project may have no initial Git commit.

Project goal
- Demonstrate a fictional, bank-neutral scam-intervention agent that can be embedded into any bank transaction flow. It is a prototype, not production banking software.
- Keep all customer, institution, transaction, and risk data fictional. Never claim a real bank integration or transmit secrets to the browser.

What is already implemented
- Next.js 16, React 19, TypeScript, Tailwind, Biome, Vitest.
- Reference customer and employee demo UI at `/dashboard`, `/send`, `/intervention/[caseId]`, `/employee`, etc.
- A reusable headless Guardian API:
  - `POST /api/v1/transactions/evaluate`
  - `GET /api/v1/cases/:caseId`
  - `POST /api/v1/cases/:caseId/messages`
  - `GET /api/v1/cases/:caseId/summary`
  - `POST /api/v1/cases/:caseId/human-decision`
- The contract and service live in `lib/guardian/`. The browser-agnostic integration demo is `/integration`.
- Provider interfaces isolate customer/recipient lookup, transactions, cases, decision callbacks, and behavioral-risk ingestion.
- Gemini is server-side only and Zod-validates structured output; a deterministic fallback works without a key.
- The customer intervention is intentionally text-only; ElevenLabs and browser speech are not part of this build.
- Remote behavioral-risk support is adapter-ready; the mocked risk engine is the default.
- The app deliberately uses in-memory demo data and an explicit demo role switch. Auth0 and deployment are not live yet.

Credential status
- A Gemini key should be configured locally in `.env.local`; verify its presence only and never print its value.
- Use `gemini-3.5-flash-lite` for new Gemini API projects; the earlier 2.5 model family may return HTTP 404 for them.
- ElevenLabs is intentionally not configured or required.
- After the user creates secrets locally, use `.env.local` (gitignored) with the names already listed in `.env.example`:
  GEMINI_API_KEY, GEMINI_MODEL,
  RISK_PROVIDER, RISK_ENGINE_URL, GUARDIAN_API_KEY, GUARDIAN_ALLOWED_ORIGIN,
  GUARDIAN_DECISION_WEBHOOK_URL, GUARDIAN_WEBHOOK_SECRET.

Suggested next implementation order
1. Verify all existing commands before changing behavior:
   `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`.
2. With the user-supplied Gemini key locally, test the server-side Gemini path without logging the credential. Confirm the deterministic fallback still works after temporarily removing the key.
3. If the user asks for live authentication, implement Auth0 using a supported Next.js server-side SDK, enforce `customer` vs `employee` roles server-side, add callback/logout configuration documentation, and retain a clearly labeled local demo mode only for development.
4. If the user asks for a deployable demo, replace in-memory repositories with a database, protect/remove `/api/demo/reset`, set `GUARDIAN_API_KEY` and a non-wildcard `GUARDIAN_ALLOWED_ORIGIN`, add rate limiting/audit storage, and document the deployment environment.
5. For another bank-app demo, do not rebuild UI components. Implement that bank’s adapters for the `lib/guardian/providers.ts` interfaces and call the v1 API contract.

Safety and quality constraints
- Never place secret values in `NEXT_PUBLIC_*`, client components, commits, logs, screenshots, or handoff messages.
- Do not collect actual bank credentials, transfer funds, or represent this as a real bank product.
- Do not weaken API key checks, origin restrictions, or server-side role enforcement merely to simplify the demo.
- Use the existing `docs/GUARDIAN_INTEGRATION.md` contract rather than creating a second incompatible API.
- Use `apply_patch` for code edits. Preserve unrelated files and do not run destructive Git commands.
- Re-run the four verification commands after changes and report results.
```

## Optional additions for the user to append

Add only the statements that match the task you want Claude Code to do next:

- "My target bank-app scenario is **[wire / ACH / card / P2P]** and the fictional institution is **[name]**. Keep the platform neutral."
- "I have added the following local variables (do not reveal them): **[variable names only]**. Test the integration and tell me only whether it works."
- "Keep Guardian text-only. Do not add ElevenLabs, browser speech, voice input, or any voice-related user interface."
- "Implement live Auth0 now. My allowed local callback is **[URL]** and my deployed callback is **[URL]**."
- "Prepare the DigitalOcean deployment configuration, but do not create paid resources or deploy until I explicitly approve it."
- "My teammate's risk engine endpoint and contract are documented in **[path]**. Build an adapter with strict timeouts and a mock fallback."
- "Do not touch the visual reference app; work only on the reusable API and provider adapters."
- "For this change, prioritize hackathon-demo reliability over production scale, but preserve the security boundaries already present."
