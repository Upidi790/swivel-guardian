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
      severity: z.number().min(0).max(1),
      explanation: z.string(),
      category: z.enum(["RISK", "NORMAL"]).optional(),
    }),
  ),
  baseline: z.object({
    median_transfer: z.number(),
    p95_transfer: z.number(),
    previous_recipient_transactions: z.number().int().nonnegative(),
  }),
});

export class RemoteRiskProvider implements RiskProvider {
  constructor(
    private readonly baseUrl: string,
    private readonly timeoutMs = 3_000,
  ) {}

  async analyzeTransaction(transaction: Transaction, _context: RiskContext): Promise<RiskAnalysis> {
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}/risk/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transaction_id: transaction.id,
        user_id: transaction.userId,
        recipient_id: transaction.recipientId ?? transaction.recipientName,
        amount: transaction.amount,
        device_id: transaction.deviceId,
        ip_region: transaction.ipRegion,
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
      signals: result.signals.map((signal) => ({ ...signal, category: signal.category ?? "RISK" })),
      baseline: {
        medianTransfer: result.baseline.median_transfer,
        p95Transfer: result.baseline.p95_transfer,
        previousRecipientTransactions: result.baseline.previous_recipient_transactions,
      },
      provider: "remote",
    };
  }
}
