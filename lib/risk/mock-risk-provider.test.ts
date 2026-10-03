import { beforeEach, describe, expect, it } from "vitest";
import { demoStore } from "@/lib/demo-store";
import { MockRiskProvider } from "@/lib/risk/mock-risk-provider";
import type { Transaction } from "@/lib/types";

const riskContext = {
  customer: {
    customerId: "maria_001",
    displayName: "Maria Rodriguez",
    normalTransferMedian: 120,
    p95Transfer: 430,
    knownDeviceIds: ["iphone_maria"],
    knownRegions: ["san_antonio"],
  },
  recipient: {
    destinationId: "recipient_elena",
    displayName: "Elena Rodriguez",
    createdAt: "2025-01-01T00:00:00.000Z",
    previousTransactionCount: 18,
    trustStatus: "TRUSTED" as const,
  },
};

function transaction(overrides: Partial<Transaction>): Transaction {
  return {
    id: "txn_test",
    userId: "maria_001",
    recipientId: "recipient_elena",
    recipientName: "Elena Rodriguez",
    amount: 80,
    memo: "Family",
    deviceId: "iphone_maria",
    ipRegion: "san_antonio",
    createdAt: new Date().toISOString(),
    status: "PENDING_INTERVENTION",
    direction: "outgoing",
    ...overrides,
  };
}

describe("MockRiskProvider", () => {
  beforeEach(() => demoStore.reset());

  it("allows a normal transfer to a known family member", async () => {
    const result = await new MockRiskProvider().analyzeTransaction(transaction({}), riskContext);
    expect(result.riskLevel).toBe("LOW");
    expect(result.requiresIntervention).toBe(false);
    expect(result.signals).toEqual(expect.arrayContaining([expect.objectContaining({ type: "KNOWN_DEVICE" })]));
  });

  it("reproduces the signature safe-device anomaly", async () => {
    const result = await new MockRiskProvider().analyzeTransaction(
      transaction({ recipientId: "recipient_secure", recipientName: "Secure Asset Services", amount: 2_000 }),
      {
        ...riskContext,
        recipient: {
          destinationId: "recipient_secure", displayName: "Secure Asset Services", createdAt: new Date().toISOString(),
          previousTransactionCount: 0, trustStatus: "UNVERIFIED",
        },
      },
    );
    expect(result.riskScore).toBe(82);
    expect(result.requiresIntervention).toBe(true);
    expect(result.signals).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "NEW_RECIPIENT" }),
        expect.objectContaining({ type: "AMOUNT_ANOMALY" }),
        expect.objectContaining({ type: "KNOWN_DEVICE", category: "NORMAL" }),
        expect.objectContaining({ type: "NORMAL_REGION", category: "NORMAL" }),
      ]),
    );
  });
});
