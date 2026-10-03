import type { CustomerContext, GuardianDecision, RecipientContext, TransactionIntent } from "@/lib/guardian/contracts";
import type { InterventionCase, Transaction, TransactionStatus } from "@/lib/types";

export interface CustomerContextProvider {
  getCustomerContext(institutionId: string, customerId: string): Promise<CustomerContext>;
}

export interface RecipientContextProvider {
  getRecipientContext(institutionId: string, transaction: TransactionIntent): Promise<RecipientContext>;
}

export interface TransactionRepository {
  save(transaction: Transaction): Promise<void>;
  get(transactionId: string): Promise<Transaction | undefined>;
  updateStatus(transactionId: string, status: TransactionStatus): Promise<void>;
}

export interface CaseRepository {
  save(caseItem: InterventionCase): Promise<void>;
  get(caseId: string): Promise<InterventionCase | undefined>;
  count(): Promise<number>;
}

export interface DecisionNotifier {
  notify(caseItem: InterventionCase, decision: GuardianDecision): Promise<void>;
}

export interface GuardianProviders {
  customerContext: CustomerContextProvider;
  recipientContext: RecipientContextProvider;
  transactions: TransactionRepository;
  cases: CaseRepository;
  decisionNotifier: DecisionNotifier;
}
