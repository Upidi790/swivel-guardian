# Guardian judge Q&A

## Is this hard-coded?

The demo contains fictional example transactions so a judge can reliably see each outcome. The production decision boundary is not tied to those examples: it accepts behavioral-risk evidence, payment context, and the customer's own explanation. Gemini is used for structured intent assessment, with a deterministic fallback when it is unavailable.

## Why pause a legitimate payment?

Unusual is not the same as fraudulent. Guardian performs a short, non-accusatory check-in and keeps the final decision with a bank employee. A plausible family, tuition, rent, or invoice explanation does not automatically cause a decline.

## Does it read texts, emails, or phone calls?

No. It uses payment and account-behavior signals plus only what the customer voluntarily enters in the safety conversation.

## What prevents the AI from blocking someone’s money?

The AI can recommend a next step, never make a final funds decision. A human employee approves release, cancellation, or trusted-recipient verification.

## Why not classify every message as a scam?

A message classifier alone cannot see whether a payment is truly unusual for this account. Guardian combines behavioral evidence with voluntary customer context, while keeping those evidence types separate for the specialist.

## How do you handle false positives?

The customer sees a short explanation, can explain the payment, and a human reviewer owns the final outcome. The product can later learn from reviewed outcomes; it does not silently expand a trusted-recipient list.

## How would this connect to a bank?

The visual demo is bank-neutral. A bank implements the provider adapters in `lib/guardian/providers.ts` and calls the versioned Guardian API before executing the transfer. Its existing transaction platform remains the system of record.

## What happens if Gemini fails?

Guardian falls back to a deterministic, explainable assessment path. It does not fail open by automatically releasing a risky payment.

## What data are you using today?

Only fictional hackathon data. The teammate-owned behavioral-risk service can replace the mock provider through the documented normalized contract.

## What is still needed for production?

Persistent encrypted storage, bank authentication and role enforcement, audit retention, rate limiting, model monitoring, policy tuning, and a reviewed integration with the bank’s transfer controls.
