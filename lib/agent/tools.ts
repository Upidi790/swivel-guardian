import patterns from "@/data/scam_patterns.json";
import type { CustomerContext, RecipientContext } from "@/lib/guardian/contracts";
import type { ChatMessage, InterventionCase } from "@/lib/types";
import type { Transaction } from "@/lib/types";

export interface AgentToolContext {
  caseItem: InterventionCase;
  transaction: Transaction;
  customer: CustomerContext;
  recipient: RecipientContext;
}

export function getTransaction(context: AgentToolContext) {
  return context.transaction;
}

export function getBehavioralRisk(context: AgentToolContext) {
  return context.caseItem.riskAnalysis;
}

export function getCustomerProfile(context: AgentToolContext) {
  return context.customer;
}

export function getRecipientHistory(context: AgentToolContext) {
  return context.recipient;
}

export function getCaseHistory(context: AgentToolContext) {
  return context.caseItem.messages;
}

export function searchScamPatterns(text: string) {
  const normalized = text.toLowerCase();
  return patterns.filter((pattern) => pattern.indicators.some((indicator) => normalized.includes(indicator)));
}

export function recordCustomerAnswer(caseItem: InterventionCase, content: string): ChatMessage {
  const message: ChatMessage = {
    id: crypto.randomUUID(),
    role: "customer",
    content,
    createdAt: new Date().toISOString(),
  };
  caseItem.messages.push(message);
  caseItem.updatedAt = message.createdAt;
  return message;
}

export function createCaseSummary(context: AgentToolContext) {
  const { caseItem, transaction } = context;
  return {
    caseId: caseItem.displayId,
    transaction: { amount: transaction.amount, recipient: transaction.recipientName, status: transaction.status },
    behavioralEvidence: caseItem.riskAnalysis.signals,
    customerStatements: caseItem.messages.filter((message) => message.role === "customer").map((message) => message.content),
    conversationSignals: caseItem.assessment.socialEngineeringSignals,
    recommendation: caseItem.assessment.nextAction,
    confidence: caseItem.assessment.confidence,
  };
}

export function recommendEscalation(caseItem: InterventionCase) {
  return {
    recommendation: "ESCALATE" as const,
    reason: caseItem.assessment.rationale,
    requiresHumanDecision: true,
  };
}
