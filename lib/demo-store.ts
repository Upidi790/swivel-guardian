import { createSeedState } from "@/lib/seed";
import type { DemoState, InterventionCase, Recipient, Transaction } from "@/lib/types";

const globalStore = globalThis as unknown as { swivelDemoState?: DemoState };

function state(): DemoState {
  globalStore.swivelDemoState ??= createSeedState();
  return globalStore.swivelDemoState;
}

export const demoStore = {
  getState: () => structuredClone(state()),
  getTransaction: (id: string) => state().transactions.find((item) => item.id === id),
  getCase: (id: string) => state().cases.find((item) => item.id === id),
  addTransaction: (transaction: Transaction) => state().transactions.unshift(transaction),
  addCase: (caseItem: InterventionCase) => state().cases.unshift(caseItem),
  updateCase: (caseItem: InterventionCase) => {
    const index = state().cases.findIndex((item) => item.id === caseItem.id);
    if (index >= 0) state().cases[index] = caseItem;
  },
  requestSupport: (caseId: string, request: "LIVE_CHAT" | "PHONE_CALL") => {
    const caseItem = state().cases.find((item) => item.id === caseId);
    if (!caseItem) return undefined;
    caseItem.supportRequest = request;
    caseItem.supportStatus = request === "LIVE_CHAT" ? "QUEUED" : "CALL_REQUESTED";
    caseItem.updatedAt = new Date().toISOString();
    caseItem.employeeNotes.push(`${request === "LIVE_CHAT" ? "Live chat" : "Phone call"} requested by customer.`);
    return structuredClone(caseItem);
  },
  updateTransactionStatus: (id: string, status: Transaction["status"]) => {
    const transaction = state().transactions.find((item) => item.id === id);
    if (transaction) transaction.status = status;
  },
  updateRecipient: (recipient: Recipient) => {
    const index = state().recipients.findIndex((item) => item.id === recipient.id);
    if (index >= 0) state().recipients[index] = recipient;
  },
  reset: () => {
    globalStore.swivelDemoState = createSeedState();
    return structuredClone(globalStore.swivelDemoState);
  },
};
