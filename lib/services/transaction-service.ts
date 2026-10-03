import { demoStore } from "@/lib/demo-store";
import { getGuardianService } from "@/lib/guardian";

export async function createPayment(input: {
  recipientId?: string;
  recipientName: string;
  amount: number;
  memo?: string;
}) {
  const { customer, cases } = demoStore.getState();
  void cases;
  const transactionId = `txn_${crypto.randomUUID().slice(0, 8)}`;
  const result = await getGuardianService().evaluate({
    transaction: {
      institutionId: "guardian_demo_credit_union",
      transactionId,
      customerId: customer.id,
      rail: "P2P",
      amount: input.amount,
      currency: "USD",
      destination: { id: input.recipientId, label: input.recipientName, type: "BUSINESS" },
      channel: "WEB",
      deviceId: customer.knownDeviceId,
      region: customer.knownRegion,
      memo: input.memo ?? "",
      metadata: { source: "legacy-reference-client" },
    },
  });
  const transaction = demoStore.getTransaction(transactionId);
  if (!transaction) throw new Error("TRANSACTION_NOT_STORED");
  if (result.outcome === "CONTINUE") {
    return { outcome: "COMPLETED" as const, transaction, risk: result.risk };
  }
  const caseItem = result.intervention ? demoStore.getCase(result.intervention.caseId) : undefined;
  if (!caseItem) throw new Error("CASE_NOT_STORED");
  return { outcome: "INTERVENTION" as const, transaction, risk: result.risk, caseItem };
}
