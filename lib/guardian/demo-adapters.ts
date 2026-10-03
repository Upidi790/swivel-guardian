import { demoStore } from "@/lib/demo-store";
import type { CustomerContext, GuardianDecision, RecipientContext, TransactionIntent } from "@/lib/guardian/contracts";
import type {
  CaseRepository,
  CustomerContextProvider,
  DecisionNotifier,
  GuardianProviders,
  RecipientContextProvider,
  TransactionRepository,
} from "@/lib/guardian/providers";
import type { InterventionCase, Transaction, TransactionStatus } from "@/lib/types";

class DemoCustomerContextProvider implements CustomerContextProvider {
  async getCustomerContext(_: string, customerId: string): Promise<CustomerContext> {
    const { customer } = demoStore.getState();
    if (customer.id !== customerId) throw new Error("CUSTOMER_CONTEXT_NOT_FOUND");
    return {
      customerId: customer.id,
      displayName: customer.name,
      normalTransferMedian: customer.medianTransfer,
      p95Transfer: customer.p95Transfer,
      knownDeviceIds: [customer.knownDeviceId],
      knownRegions: [customer.knownRegion],
    };
  }
}

class DemoRecipientContextProvider implements RecipientContextProvider {
  async getRecipientContext(_: string, transaction: TransactionIntent): Promise<RecipientContext> {
    const recipient = demoStore
      .getState()
      .recipients.find(
        (item) =>
          item.id === transaction.destination.id || item.name.toLowerCase() === transaction.destination.label.toLowerCase(),
      );
    return {
      destinationId: transaction.destination.id,
      displayName: transaction.destination.label,
      createdAt: recipient?.createdAt ?? new Date().toISOString(),
      previousTransactionCount: recipient?.previousTransactionCount ?? 0,
      trustStatus: recipient?.trustStatus ?? "UNVERIFIED",
    };
  }
}

class DemoTransactionRepository implements TransactionRepository {
  async save(transaction: Transaction): Promise<void> {
    const existing = demoStore.getTransaction(transaction.id);
    if (!existing) demoStore.addTransaction(transaction);
  }
  async get(transactionId: string) {
    return demoStore.getTransaction(transactionId);
  }
  async updateStatus(transactionId: string, status: TransactionStatus) {
    demoStore.updateTransactionStatus(transactionId, status);
  }
}

class DemoCaseRepository implements CaseRepository {
  async save(caseItem: InterventionCase): Promise<void> {
    const existing = demoStore.getCase(caseItem.id);
    if (existing) demoStore.updateCase(caseItem);
    else demoStore.addCase(caseItem);
  }
  async get(caseId: string) {
    return demoStore.getCase(caseId);
  }
  async count() {
    return demoStore.getState().cases.length;
  }
}

class DemoDecisionNotifier implements DecisionNotifier {
  async notify(caseItem: InterventionCase, decision: GuardianDecision): Promise<void> {
    const webhookUrl = process.env.GUARDIAN_DECISION_WEBHOOK_URL;
    if (!webhookUrl) {
      console.info(
        `[Guardian integration] Simulated decision notification: ${decision.action} for ${caseItem.transactionId}.`,
      );
      return;
    }
    const response = await fetch(webhookUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(process.env.GUARDIAN_WEBHOOK_SECRET
          ? { Authorization: `Bearer ${process.env.GUARDIAN_WEBHOOK_SECRET}` }
          : {}),
      },
      body: JSON.stringify({
        event: "guardian.human_decision",
        contractVersion: "1.0",
        caseId: caseItem.id,
        transactionId: caseItem.transactionId,
        action: decision.action,
        decidedBy: decision.decidedBy,
      }),
      signal: AbortSignal.timeout(5_000),
    });
    if (!response.ok) throw new Error(`Decision webhook returned HTTP ${response.status}`);
  }
}

export function createDemoProviders(): GuardianProviders {
  return {
    customerContext: new DemoCustomerContextProvider(),
    recipientContext: new DemoRecipientContextProvider(),
    transactions: new DemoTransactionRepository(),
    cases: new DemoCaseRepository(),
    decisionNotifier: new DemoDecisionNotifier(),
  };
}
