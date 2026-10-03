import type { CustomerContext, RecipientContext } from "@/lib/guardian/contracts";
import type { RiskAnalysis, Transaction } from "@/lib/types";

export interface RiskContext {
  customer: CustomerContext;
  recipient: RecipientContext;
}

export interface RiskProvider {
  analyzeTransaction(transaction: Transaction, context: RiskContext): Promise<RiskAnalysis>;
}
