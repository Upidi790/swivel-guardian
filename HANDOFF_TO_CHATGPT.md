# Handoff: Claude Code → ChatGPT

**Project:** SWIVEL Guardian — AI scam-intervention prototype (RowdyHacks XII)
**Date:** 2026-10-03
**Repo state:** `master`, 2 commits, clean working tree
**Verification at handoff:** 14/14 tests · clean typecheck · clean lint · clean build

This document is written for ChatGPT, to pick up the work without re-reading the
whole repository. It describes an audit-and-repair pass over the prototype that
Codex had built, not a rewrite.

---

## 0. What I was asked to do

Act as the senior engineer reviewing a partially-built hackathon project:
audit it, run it, compare against the product vision, fix the highest-value
gaps, preserve everything that already worked, and verify the demo end to end.

Explicitly **not** a redesign.

---

## 1. Headline finding

**Codex's work was substantially better than the handoff implied.** Every item
on the vision's MUST-HAVE list was already built and working, including real
Gemini integration — not a chatbot wrapper. Before I changed anything:

- `npm test` 8/8, `npm run typecheck` clean, `npm run lint` clean on 56 files
- The signature Maria scenario produced case #1042 at 82/100, escalated, and
  landed in the employee queue with behavioral and conversation evidence kept
  visually separate
- Live Gemini asked its *own* adaptive follow-up rather than a canned question,
  and returned a Zod-validated structured assessment
- All four test scenarios (A/B/C/D) behaved correctly

So this pass fixed **defects on the non-scripted paths**, removed dead code, and
completed two half-built features. I preserved the architecture as-is.

---

## 2. Audit method

I did not trust the handoff docs or the README. I:

1. Read every source file (`app/`, `components/`, `lib/`, `data/`, `docs/`)
2. Ran `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`
3. Verified the configured Gemini model (`gemini-3.5-flash-lite`) actually
   exists on the project's key by listing models, then issued a live
   `generateContent` call with the app's exact request shape — HTTP 200
4. Drove the running app over HTTP with `curl` for all four scenarios, plus a
   degraded-mode run with no Gemini key and an unreachable risk engine
5. `grep`-ed for which routes the UI actually calls, which exposed a whole dead
   API layer

Every claim in section 5 below was observed, not inferred.

---

## 3. Problems found

| # | Problem | Severity |
|---|---|---|
| P1 | **`ALLOW`/`REVIEW` was a dead end.** `lib/guardian/service.ts` handled only `ESCALATE`. A customer who gave a legitimate explanation left the case `OPEN` and the payment `PENDING_INTERVENTION` **forever**, staring at a chat box with no question and no resolution. Observed live. | Demo-breaking |
| P2 | Gemini's `customerExplanation` was written *about* the customer, into her own chat: *"The customer is voluntarily paying tuition for her daughter Elena…"*. The system prompt never said to use second person. | High |
| P3 | README scripted three customer replies; live Gemini concludes after the **second**, so reply 3 returned `409 CASE_CLOSED` and **`URGENCY` + `SECRECY_REQUEST` never appeared** — the two signals the pitch leans on hardest. | High |
| P4 | `app/employee/cases/[caseId]/page.tsx` hardcoded `"{nextAction} FOR HUMAN VERIFICATION"`, so non-escalated cases read "ALLOW FOR HUMAN VERIFICATION". | Medium |
| P5 | A **complete second API** that no UI called: `app/api/transactions`, `app/api/interventions`, `app/api/employee/.../actions`, plus `lib/services/` and `lib/validation.ts`. One route self-labeled `decidedBy: "legacy_employee_route"`. | Medium (confusing) |
| P6 | **`TRUSTED` was unreachable.** Trust could be requested but never granted — the approval half was missing. Trust also had zero effect on risk scoring, making the feature decorative. | Medium |
| P7 | `lib/seed.ts` pinned `now` to a literal `2026-10-03T18:00`. Correct that day only; the next day `RECIPIENT_RECENTLY_ADDED` would silently vanish from the evidence list. | Latent |
| P8 | `lib/risk/mock-risk-provider.ts` force-set `score = 82` for the exact demo scenario. The organic arithmetic already produces 82, so the override was redundant and only invited a judge asking "is this faked?" | Credibility |
| P9 | `components/payment-form.tsx` sends `customerId`, `deviceId`, and `region` **from the browser** — the exact fields the risk engine trusts. Fine for a prototype, but undocumented. | Documentation |
| P10 | **The repo had zero git commits.** Everything untracked. One bad edit would have lost the project. | Critical |

---

## 4. Changes made

### P10 — Git safety net (done first)

Two commits now exist: `39ac3d0` is the untouched Codex baseline, `a9361da` is
this pass. Any change can be diffed or reverted. `.env.local` is gitignored and
not tracked.

### P1 — Exhaustive interview outcomes (the important one)

Added `INTERVIEW_OUTCOMES` in `lib/guardian/service.ts`, a table mapping every
agent action to a case state, a payment state, and a closing customer-facing
message. `addMessage` now applies it; `isCaseClosed()` replaced the partial
status check so a concluded interview rejects further answers.

This turned a bug fix into an architectural asset. The agent's authority is now
**deliberately asymmetric**, which is a one-sentence pitch to judges:

> The agent may pause a payment, may release the pause it created itself, and
> may recommend human review. It has no entry for cancel, deny, or freeze.

| Agent `nextAction` | Case | Payment |
|---|---|---|
| `ASK_FOLLOW_UP` | stays `OPEN` | stays `PENDING_INTERVENTION` |
| `ALLOW` | `RESOLVED` / `RELEASED` | `COMPLETED` |
| `REVIEW` | `REVIEWED` | `UNDER_REVIEW` — employee confirms |
| `ESCALATE` | `ESCALATED` | `UNDER_REVIEW` — employee decides |
| *(no entry exists)* | — | `CANCELLED` is **human-only** |

A test asserts `CANCELLED` is reachable only through `applyHumanDecision`.

### P2 — Prompt rules (`lib/agent/prompt.ts`)

Three rules added to `AGENT_SYSTEM_PROMPT`:

1. Write `customerExplanation` and `nextQuestion` **to** the customer in second
   person; analysis for staff goes in `rationale`
2. Populate `socialEngineeringSignals` using only the exact `id` values from
   `data/scam_patterns.json` — never invented prose
3. Explicit criteria for choosing each `nextAction`

Rule 2 is also enforced structurally: `lib/agent/gemini.ts` now generates an
`enum` for `socialEngineeringSignals` from the pattern file, so the taxonomy is
a contract rather than a convention.

### P3 — Quick replies restructured (`components/intervention-experience.tsx`)

Replaced the flat 4-element array (sliced two at a time by message count) with
`quickReplyTurns`: one pair of suggested answers per turn, each pair offering a
scam path **and** a benign path. The second turn's scam reply now carries the
authority claim, the threat, the deadline, and the secrecy request together, so
all five signals surface in the two turns Gemini actually permits.

I deliberately did **not** delay escalation to pad the transcript — fixing the
copy was correct; weakening the safety behavior would not have been.

Also added released-vs-review banner states and extended `closed` to cover all
non-open statuses.

### P6 — Trusted-recipient workflow completed

- New `app/api/recipients/[recipientId]/trust-decision/route.ts` — simulated
  employee + second-factor approval. Rejects approval without a verified second
  factor, and rejects anything not in `TRUST_REQUESTED`.
- New `components/trust-requests.tsx` — approve/deny UI on the employee queue.
- The **customer-facing route still reaches only `TRUST_REQUESTED`**, so trust
  cannot be self-granted to escape an intervention.
- `MockRiskProvider` now gives verified trust a bounded −10 benefit **that an
  extreme amount overrides**, with a signal explaining why. Verified: $80 to a
  trusted recipient scores 0 and continues; **$2,000 to the same trusted
  recipient still intervenes.**

### P4, P5, P7, P8, P9

- Recommendation card uses a `RECOMMENDATION_LABELS` map per action
- Deleted the entire dead API layer; the app now has exactly one API (`/api/v1`),
  matching `docs/GUARDIAN_INTEGRATION.md`
- `lib/seed.ts` derives all timestamps from `Date.now()`
- Score override removed — 82/100 now emerges from the weights alone
  (8 base + 26 new recipient + 34 amount + 14 recency)
- `docs/SECURITY.md` gained a "Known prototype boundaries" section naming the
  client-supplied device/region fields, the open-by-default headless API, the
  unauthenticated reset endpoint, and the simulated second factor
- `lib/agent/gemini.ts` now logs the missing-key fallback instead of falling
  back silently

### Tests and docs

`lib/guardian/service.test.ts` grew from 3 to 9 tests (suite: 8 → 14), covering
each of the four outcomes, the closed-case rejection, and the no-cancel
guarantee. The agent module is `vi.mock`-ed so outcome handling is tested
independently of Gemini and the network.

README now documents the agent's authority table, and its demo script matches
observed live behavior.

---

## 5. Verification — what I actually ran

```
npm test       → 14/14 passed
npm run typecheck → clean
npm run lint   → clean (52 files)
npm run build  → clean, all 19 routes
```

Walked over HTTP against the running app with the live Gemini key:

| Scenario | Observed result |
|---|---|
| A — $80 → trusted daughter | `CONTINUE`, score **0**, no case created |
| **Trust bypass guard** — $2,000 → *same trusted* daughter | still **`INTERVENE`**, signal explains trust did not reduce the score |
| B — $1,500 new recipient, legitimate tuition explanation | `ALLOW` → case `RESOLVED`, transaction **`COMPLETED`**, further answers `409` *(this is the P1 regression test)* |
| C/D — $2,000, known device, normal region | **82/100** organically, `ESCALATE`, case `ESCALATED`, txn `UNDER_REVIEW`, and all **five** signals: `AUTHORITY_IMPERSONATION, EXTERNAL_INSTRUCTION, URGENCY, THREAT, SECRECY_REQUEST` |
| Employee flow | Case detail renders separated evidence + `ESCALATE FOR HUMAN VERIFICATION`; human decision moves case to `RESOLVED` |
| Trust workflow | request → self-approve **blocked** (`SECOND_FACTOR_REQUIRED`) → employee+2FA → `TRUSTED` → replay `409 NO_PENDING_TRUST_REQUEST` |
| **Degraded mode** (no Gemini key + unreachable risk engine) | Full demo completes, tagged `provider: remote-fallback` and `modelSource: deterministic-fallback`, still produces all 5 signals and escalates |

Scenario D is the conceptually important one: correct authenticated customer,
known device, normal location, large unusual payment, social-engineering
indicators → `ESCALATE`. That proves the system detects scam-*induced
authorized* payments, not merely account takeover.

---

## 6. Current architecture

```
Customer UI (/dashboard, /send)
        │
        ▼
POST /api/v1/transactions/evaluate          ← the only API; institution-neutral
        │
        ▼
GuardianService.evaluate()
        │
        ├── RiskProvider  ──┬── MockRiskProvider        (default)
        │                   ├── RemoteRiskProvider      (teammate's model)
        │                   └── FallbackRiskProvider    (3s timeout → mock, logged)
        │                   └── or risk supplied inline on the request
        ▼
   requiresIntervention?
    ├── no  → transaction COMPLETED, outcome CONTINUE
    └── yes → case created, outcome INTERVENE
                  │
                  ▼
        POST /api/v1/cases/:id/messages  (adaptive interview)
                  │
                  ├── assessWithGemini()  → Zod-validated structured assessment
                  │       └── on any failure → runDeterministicAgent()
                  ▼
            INTERVIEW_OUTCOMES → case + payment state + closing message
                  │
                  ▼
        Employee dashboard (/employee) → POST /api/v1/cases/:id/human-decision
                                              └── final decision, incl. CANCEL
```

Provider interfaces in `lib/guardian/providers.ts` isolate customer lookup,
recipient lookup, transaction storage, case storage, and the decision webhook.
The demo uses in-memory adapters; another institution swaps adapters without
touching prompts or UI.

---

## 7. Teammate integration (behavioral risk model)

**Nothing new is required of her.** `docs/RISK_ENGINE_INTEGRATION.md` is
complete: endpoint, request/response schemas, TypeScript types, sample curl,
timeout and failure behavior, and the env switch.

Two integration paths, both already working:

1. **Service:** she serves `POST /risk/analyze` with the documented snake_case
   body; we set `RISK_PROVIDER=remote` and `RISK_ENGINE_URL=<her url>`.
   `FallbackRiskProvider` covers her service being down — falls back to mock,
   tags the result `remote-fallback`, and logs it visibly.
2. **Inline (zero coupling):** pass a `behavioralRisk` object on
   `POST /api/v1/transactions/evaluate`. Already exercised by
   `lib/guardian/service.test.ts`.

Tiger Data stays entirely behind her service. This app is not coupled to it.

---

## 8. Remaining limitations

- **In-memory state.** `lib/demo-store.ts` keeps everything in a `globalThis`
  object; it dies on restart. Fine for the demo, must become a database before
  any deployment.
- **No real authentication.** The customer/employee switch in
  `components/app-shell.tsx` is a labeled demo toggle. Auth0 is absent by
  design — the vision said not to let auth block the demo.
- **Trust second factor is asserted, not verified** (`secondFactorVerified`
  boolean). The property that matters still holds: customers cannot self-grant.
- **Client supplies its own device/region.** Documented in `docs/SECURITY.md`.
- **`/api/demo/reset` is unauthenticated** and wipes all state.
- **No rate limiting, CSRF protection, or append-only audit log.**
- **ElevenLabs is intentionally absent** — text-only is a stated design choice.
- **Dense one-line JSX** in `app/employee/**` and `app/dashboard`. Ugly to read
  but working; I deliberately left it alone rather than risk the demo for zero
  judge-visible gain.

---

## 9. Highest-value next step

**Rehearse the demo out loud, clicking through the UI.** Everything above was
verified through the API; I never saw the rendered pages. The logic is sound, so
the biggest remaining risk is presentational — the 90 seconds of narration, and
whether anything looks wrong on screen.

If there is time after that, the next most valuable item is replacing the
in-memory store with SQLite or Postgres, which is the single blocker to a
deployable demo.

---

## 10. Constraints to keep respecting

- **Never put the Gemini key anywhere but `.env.local`** (gitignored, untracked,
  and excluded from the distributed zip). Not in `NEXT_PUBLIC_*`, commits, logs,
  screenshots, or handoff messages.
- Don't weaken `GUARDIAN_API_KEY` checks, origin restrictions, or the
  customer-cannot-self-grant-trust rule to simplify a demo.
- Use the existing `docs/GUARDIAN_INTEGRATION.md` contract; do not create a
  second incompatible API — one was just removed.
- Keep all customer, institution, and transaction data fictional. This is a
  prototype, not a bank product, and must not be represented as one.
- Keep behavioral evidence and conversation evidence distinct in both code and
  UI. Do not collapse them into a single "AI fraud probability".
