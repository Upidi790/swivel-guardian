import { z } from "zod";

export const paymentRailSchema = z.enum(["ACH", "CARD", "WIRE", "RTP", "P2P", "LOAN_PAYMENT", "INTERNAL_TRANSFER"]);
export const paymentChannelSchema = z.enum(["WEB", "MOBILE", "BRANCH", "CALL_CENTER", "IVR"]);
export const destinationTypeSchema = z.enum(["PERSON", "BUSINESS", "ACCOUNT", "LOAN"]);

export const transactionIntentSchema = z.object({
  institutionId: z.string().trim().min(2).max(100),
  transactionId: z.string().trim().min(3).max(150),
  customerId: z.string().trim().min(2).max(150),
  rail: paymentRailSchema,
  amount: z.coerce.number().positive().max(10_000_000),
  currency: z.string().trim().length(3).transform((value) => value.toUpperCase()).default("USD"),
  destination: z.object({
    id: z.string().trim().min(1).max(150).optional(),
    label: z.string().trim().min(2).max(150),
    type: destinationTypeSchema,
  }),
  channel: paymentChannelSchema,
  deviceId: z.string().trim().max(200).optional(),
  region: z.string().trim().max(100).optional(),
  memo: z.string().trim().max(280).optional().default(""),
  metadata: z.record(z.string(), z.unknown()).optional().default({}),
});

export const customerContextSchema = z.object({
  customerId: z.string(),
  displayName: z.string().min(1),
  normalTransferMedian: z.number().nonnegative(),
  p95Transfer: z.number().nonnegative(),
  knownDeviceIds: z.array(z.string()),
  knownRegions: z.array(z.string()),
});

export const recipientContextSchema = z.object({
  destinationId: z.string().optional(),
  displayName: z.string(),
  createdAt: z.string().datetime(),
  previousTransactionCount: z.number().int().nonnegative(),
  trustStatus: z.enum(["TRUSTED", "UNVERIFIED", "TRUST_REQUESTED"]),
});

export const suppliedRiskAnalysisSchema = z.object({
  riskScore: z.number().min(0).max(100),
  riskLevel: z.enum(["LOW", "MEDIUM", "HIGH"]),
  requiresIntervention: z.boolean(),
  signals: z.array(
    z.object({
      type: z.string(),
      severity: z.number().min(0).max(1),
      explanation: z.string(),
      category: z.enum(["RISK", "NORMAL"]),
    }),
  ),
  baseline: z.object({
    medianTransfer: z.number(),
    p95Transfer: z.number(),
    previousRecipientTransactions: z.number().int().nonnegative(),
  }),
});

export const guardianEvaluateRequestSchema = z.object({
  transaction: transactionIntentSchema,
  customerContext: customerContextSchema.optional(),
  recipientContext: recipientContextSchema.optional(),
  behavioralRisk: suppliedRiskAnalysisSchema.optional(),
});

export const guardianMessageRequestSchema = z.object({
  message: z.string().trim().min(1).max(2_000),
});

export const guardianDecisionRequestSchema = z.object({
  action: z.enum(["MARK_REVIEWED", "RELEASE", "KEEP_UNDER_REVIEW", "CANCEL"]),
  decidedBy: z.string().trim().min(2).max(150).default("demo_employee"),
});

export type TransactionIntent = z.infer<typeof transactionIntentSchema>;
export type CustomerContext = z.infer<typeof customerContextSchema>;
export type RecipientContext = z.infer<typeof recipientContextSchema>;
export type GuardianEvaluateRequest = z.infer<typeof guardianEvaluateRequestSchema>;
export type GuardianDecision = z.infer<typeof guardianDecisionRequestSchema>;

export interface GuardianEvaluationResponse {
  contractVersion: "1.0";
  institutionId: string;
  transactionId: string;
  outcome: "CONTINUE" | "INTERVENE";
  transactionStatus: string;
  risk: import("@/lib/types").RiskAnalysis;
  intervention: null | {
    caseId: string;
    displayId: string;
    status: string;
    sessionPath: string;
    firstMessage: string;
  };
}
