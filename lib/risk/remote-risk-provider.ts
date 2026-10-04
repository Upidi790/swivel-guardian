import { z } from "zod";
import type { RiskContext, RiskProvider } from "@/lib/risk/provider";
import type { RiskAnalysis, Transaction } from "@/lib/types";

const remoteResponseSchema = z.object({
  transaction_id: z.string(),
  risk_score: z.number().min(0).max(100),
  risk_level: z.enum(["LOW", "MEDIUM", "HIGH"]),
  requires_intervention: z.boolean(),
  signals: z.array(
    z.object({
      type: z.string(),
      severity: z.number().min(0).max(1).optional(),
      points: z.number().nonnegative().optional(),
      explanation: z.string(),
      category: z.enum(["RISK", "NORMAL"]).optional(),
    }),
  ),
  baseline: z.object({
    median_transfer: z.number().optional(),
    p95_transfer: z.number().optional(),
    previous_recipient_transactions: z.number().int().nonnegative().optional(),
  }),
});

export class RemoteRiskProvider implements RiskProvider {
  constructor(
    private readonly baseUrl: string,
    private readonly timeoutMs = 3_000,
  ) {}

  async analyzeTransaction(transaction: Transaction, context: RiskContext): Promise<RiskAnalysis> {
    const path = process.env.RISK_ENGINE_PATH ?? "/analyze";
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transaction_id: transaction.id,
        // The handoff database contains synthetic fixture profiles rather than
        // Maria's application ID. This explicit demo-only mapping lets the
        // reference UI exercise the real engine without claiming that its
        // fixture history belongs to Maria.
        user_id: process.env.RISK_ENGINE_DEMO_USER_ID ?? transaction.userId,
        timestamp: transaction.createdAt.replace(/\.\d{3}Z$/, "Z"),
        currency: transaction.currency ?? "USD",
        recipient_id: transaction.recipientId ?? transaction.recipientName,
        recipient_type: transaction.destinationType?.toLowerCase() ?? "transfer",
        recipient_first_seen: context.recipient.createdAt,
        amount: transaction.amount,
        device_id: transaction.deviceId,
        ip_region: transaction.ipRegion,
        transaction_type: "transfer",
        successful: false,
      }),
      signal: AbortSignal.timeout(this.timeoutMs),
      cache: "no-store",
    });
    if (!response.ok) throw new Error(`Risk engine returned HTTP ${response.status}`);
    const result = remoteResponseSchema.parse(await response.json());
    return {
      transactionId: result.transaction_id,
      riskScore: result.risk_score,
      riskLevel: result.risk_level,
      requiresIntervention: result.requires_intervention,
      signals: result.signals.map((signal) => ({
        type: signal.type,
        severity: signal.severity ?? Math.min(1, (signal.points ?? 0) / 25),
        explanation: signal.explanation,
        category: signal.category ?? "RISK",
      })),
      baseline: {
        medianTransfer: result.baseline.median_transfer ?? 0,
        p95Transfer: result.baseline.p95_transfer ?? 0,
        previousRecipientTransactions: result.baseline.previous_recipient_transactions ?? 0,
      },
      provider: "remote",
    };
  }
}
