# Behavioral Risk Engine Integration

Guardian consumes the teammate-owned behavioral/anomaly model through one `RiskProvider` interface. No UI or intervention-agent code depends on the model implementation.

## Configuration

```env
RISK_PROVIDER=remote
RISK_ENGINE_URL=http://localhost:8000
RISK_ENGINE_TIMEOUT_MS=3000
RISK_FALLBACK_TO_MOCK=true
```

- `RISK_PROVIDER=mock` uses deterministic local scoring.
- `RISK_PROVIDER=remote` calls the URL below.
- When `RISK_FALLBACK_TO_MOCK=true`, a timeout, network failure, non-2xx response, or malformed response is logged and the transaction is scored by the mock provider with `provider: "remote-fallback"`.
- Set `RISK_FALLBACK_TO_MOCK=false` when a remote failure should fail the payment request instead.

## Exact endpoint

```http
POST {RISK_ENGINE_URL}/risk/analyze
Content-Type: application/json
```

The default timeout is 3,000 ms. The route should be idempotent for a repeated `transaction_id`.

## Request schema

```ts
interface RiskEngineRequest {
  transaction_id: string; // required, unique transaction identifier
  user_id: string;        // required
  recipient_id: string;   // required; recipient ID or stable name fallback
  amount: number;         // required; positive USD amount
  device_id: string;      // required
  ip_region: string;      // required; normalized region slug
}
```

All six fields are currently required. Future optional signals should be accepted without making existing fields incompatible.

## Response schema

```ts
type RiskLevel = "LOW" | "MEDIUM" | "HIGH";
type SignalCategory = "RISK" | "NORMAL";

interface RiskEngineResponse {
  transaction_id: string;
  risk_score: number; // 0–100
  risk_level: RiskLevel;
  requires_intervention: boolean;
  signals: Array<{
    type: string;
    severity: number; // 0–1
    explanation: string;
    category?: SignalCategory; // optional, defaults to RISK
  }>;
  baseline: {
    median_transfer: number;
    p95_transfer: number;
    previous_recipient_transactions: number; // integer >= 0
  };
}
```

The response is validated at runtime with Zod. Unknown response fields are ignored. Missing or invalid required fields trigger the declared error behavior.

## Sample request

```bash
curl -X POST http://localhost:8000/risk/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_1001",
    "user_id": "maria_001",
    "recipient_id": "recipient_900",
    "amount": 2000,
    "device_id": "iphone_maria",
    "ip_region": "san_antonio"
  }'
```

## Sample response

```json
{
  "transaction_id": "txn_1001",
  "risk_score": 82,
  "risk_level": "HIGH",
  "requires_intervention": true,
  "signals": [
    {
      "type": "NEW_RECIPIENT",
      "severity": 1,
      "explanation": "No previous transactions exist for this recipient.",
      "category": "RISK"
    },
    {
      "type": "KNOWN_DEVICE",
      "severity": 0,
      "explanation": "The payment came from Maria's recognized device.",
      "category": "NORMAL"
    }
  ],
  "baseline": {
    "median_transfer": 120,
    "p95_transfer": 430,
    "previous_recipient_transactions": 0
  }
}
```

## Switching providers

No code change is required. Set `RISK_PROVIDER=remote`, set `RISK_ENGINE_URL`, and restart Next.js. The implementation lives in `lib/risk/remote-risk-provider.ts`; the shared contract is `lib/risk/provider.ts`.

## Error behavior

The adapter treats connection failures, timeouts, non-2xx HTTP status, invalid JSON, and schema violations as provider failures. With fallback enabled, the server writes an explicit warning and returns deterministic mock analysis marked `remote-fallback`; it never silently claims the remote model was used. With fallback disabled, the transaction API returns a user-safe error and leaves no completed transaction.
