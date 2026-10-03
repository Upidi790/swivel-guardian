import { describe, expect, it, vi } from "vitest";
import type { GuardianEvaluateRequest } from "@/lib/guardian/contracts";
import type { GuardianProviders } from "@/lib/guardian/providers";
import { GuardianService } from "@/lib/guardian/service";
import type { RiskProvider } from "@/lib/risk";
import type { InterventionCase, Transaction } from "@/lib/types";

function harness() {
  const transactions = new Map<string, Transaction>();
  const cases = new Map<string, InterventionCase>();
  const notify = vi.fn();
  const providers: GuardianProviders = {
    customerContext: { getCustomerContext: vi.fn(() => Promise.reject(new Error("should use supplied context"))) },
    recipientContext: { getRecipientContext: vi.fn(() => Promise.reject(new Error("should use supplied context"))) },
    transactions: {
      save: vi.fn(async (transaction) => { transactions.set(transaction.id, transaction); }),
      get: vi.fn(async (id) => transactions.get(id)),
      updateStatus: vi.fn(async (id, status) => {
        const transaction = transactions.get(id);
        if (transaction) transaction.status = status;
      }),
    },
    cases: {
      save: vi.fn(async (caseItem) => { cases.set(caseItem.id, caseItem); }),
      get: vi.fn(async (id) => cases.get(id)),
      count: vi.fn(async () => cases.size),
    },
    decisionNotifier: { notify },
  };
  const unusedRiskProvider: RiskProvider = {
    analyzeTransaction: vi.fn(() => Promise.reject(new Error("should use supplied risk"))),
  };
  return { service: new GuardianService(providers, unusedRiskProvider), transactions, cases, notify };
}

function request(requiresIntervention: boolean): GuardianEvaluateRequest {
  return {
    transaction: {
      institutionId: "portable_partner_bank",
      transactionId: `external_${requiresIntervention ? "high" : "low"}`,
      customerId: "customer_external_42",
      rail: "WIRE",
      amount: requiresIntervention ? 4_500 : 75,
      currency: "USD",
      destination: { id: "counterparty_1", label: "External Counterparty", type: "BUSINESS" },
      channel: "MOBILE",
      deviceId: "known_device",
      region: "austin",
      memo: "Vendor payment",
      metadata: {},
    },
    customerContext: {
      customerId: "customer_external_42",
      displayName: "External Bank Customer",
      normalTransferMedian: 110,
      p95Transfer: 480,
      knownDeviceIds: ["known_device"],
      knownRegions: ["austin"],
    },
    recipientContext: {
      destinationId: "counterparty_1",
      displayName: "External Counterparty",
      createdAt: new Date().toISOString(),
      previousTransactionCount: requiresIntervention ? 0 : 8,
      trustStatus: requiresIntervention ? "UNVERIFIED" : "TRUSTED",
    },
    behavioralRisk: {
      riskScore: requiresIntervention ? 88 : 9,
      riskLevel: requiresIntervention ? "HIGH" : "LOW",
      requiresIntervention,
      signals: [
        {
          type: requiresIntervention ? "AMOUNT_ANOMALY" : "NORMAL_AMOUNT",
          severity: requiresIntervention ? 0.96 : 0,
          explanation: requiresIntervention ? "Amount is outside the external customer's normal range." : "Amount is normal.",
          category: requiresIntervention ? "RISK" : "NORMAL",
        },
      ],
      baseline: { medianTransfer: 110, p95Transfer: 480, previousRecipientTransactions: requiresIntervention ? 0 : 8 },
    },
  };
}

describe("GuardianService portability", () => {
  it("continues a low-risk transaction without knowing the bank UI", async () => {
    const { service, transactions } = harness();
    const response = await service.evaluate(request(false));
    expect(response).toMatchObject({ contractVersion: "1.0", institutionId: "portable_partner_bank", outcome: "CONTINUE" });
    expect(transactions.get("external_low")?.status).toBe("COMPLETED");
  });

  it("creates an institution-scoped intervention from a supplied risk model", async () => {
    const { service, cases } = harness();
    const response = await service.evaluate(request(true));
    expect(response.outcome).toBe("INTERVENE");
    expect(response.intervention?.sessionPath).toMatch(/^\/intervention\/case_/);
    const caseItem = [...cases.values()][0];
    expect(caseItem.institutionId).toBe("portable_partner_bank");
    expect(caseItem.contextSnapshot.customer.displayName).toBe("External Bank Customer");
  });

  it("notifies the integrating institution only after a human decision", async () => {
    const { service, notify } = harness();
    const response = await service.evaluate(request(true));
    await service.applyHumanDecision(response.intervention?.caseId ?? "", {
      action: "KEEP_UNDER_REVIEW",
      decidedBy: "partner_fraud_specialist",
    });
    expect(notify).toHaveBeenCalledOnce();
    expect(notify.mock.calls[0][1]).toMatchObject({ action: "KEEP_UNDER_REVIEW" });
  });
});
