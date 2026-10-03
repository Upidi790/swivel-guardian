import { initialAssessment } from "@/lib/agent/deterministic-agent";
import { assessWithGemini } from "@/lib/agent/gemini";
import { createCaseSummary, recordCustomerAnswer } from "@/lib/agent/tools";
import type {
  GuardianDecision,
  GuardianEvaluateRequest,
  GuardianEvaluationResponse,
  TransactionIntent,
} from "@/lib/guardian/contracts";
import type { GuardianProviders } from "@/lib/guardian/providers";
import { getRiskProvider, type RiskProvider } from "@/lib/risk";
import type { CaseStatus, InterventionCase, RiskAnalysis, Transaction, TransactionStatus } from "@/lib/types";

function toStoredTransaction(intent: TransactionIntent): Transaction {
  return {
    id: intent.transactionId,
    userId: intent.customerId,
    recipientId: intent.destination.id,
    recipientName: intent.destination.label,
    amount: intent.amount,
    memo: intent.memo,
    deviceId: intent.deviceId ?? "unknown",
    ipRegion: intent.region ?? "unknown",
    createdAt: new Date().toISOString(),
    status: "PENDING_INTERVENTION",
    direction: "outgoing",
    institutionId: intent.institutionId,
    rail: intent.rail,
    currency: intent.currency,
    channel: intent.channel,
    destinationType: intent.destination.type,
  };
}

function fromSuppliedRisk(request: GuardianEvaluateRequest): RiskAnalysis | undefined {
  if (!request.behavioralRisk) return undefined;
  return {
    transactionId: request.transaction.transactionId,
    ...request.behavioralRisk,
    provider: "remote",
  };
}

/**
 * How the agent is allowed to conclude an interview.
 *
 * The agent can release only the hold it created itself, or hand the case to a
 * human. It has no entry here for cancelling a payment, denying funds, or
 * freezing an account -- those remain human-only decisions in
 * `applyHumanDecision`. `ASK_FOLLOW_UP` is absent on purpose: it leaves the
 * case OPEN so the conversation continues.
 */
const INTERVIEW_OUTCOMES: Record<
  "ALLOW" | "REVIEW" | "ESCALATE",
  {
    caseStatus: CaseStatus;
    transactionStatus: TransactionStatus;
    resolution?: InterventionCase["resolution"];
    closing: string;
  }
> = {
  ALLOW: {
    caseStatus: "RESOLVED",
    resolution: "RELEASED",
    transactionStatus: "COMPLETED",
    closing:
      "Nothing you described matches the pressure, threat, or secrecy patterns we look for, so we have released this payment. Thank you for confirming.",
  },
  REVIEW: {
    caseStatus: "REVIEWED",
    resolution: "UNDER_REVIEW",
    transactionStatus: "UNDER_REVIEW",
    closing:
      "Because the amount and this recipient are still unusual for your account, a member of our team will confirm the payment with you before it goes out. It is on hold, not cancelled.",
  },
  ESCALATE: {
    caseStatus: "ESCALATED",
    transactionStatus: "UNDER_REVIEW",
    closing:
      "Your payment will stay pending while a bank employee reviews it with you. A real bank will never ask you to keep a payment secret from your family.",
  },
};

export function isCaseClosed(status: CaseStatus) {
  return status !== "OPEN";
}

export class GuardianService {
  constructor(
    private readonly providers: GuardianProviders,
    private readonly riskProvider: RiskProvider = getRiskProvider(),
  ) {}

  async evaluate(request: GuardianEvaluateRequest): Promise<GuardianEvaluationResponse> {
    const { transaction: intent } = request;
    const existing = await this.providers.transactions.get(intent.transactionId);
    if (existing) throw new Error("TRANSACTION_ALREADY_EVALUATED");

    const customer =
      request.customerContext ??
      (await this.providers.customerContext.getCustomerContext(intent.institutionId, intent.customerId));
    const recipient =
      request.recipientContext ??
      (await this.providers.recipientContext.getRecipientContext(intent.institutionId, intent));
    const transaction = toStoredTransaction(intent);
    const risk =
      fromSuppliedRisk(request) ??
      (await this.riskProvider.analyzeTransaction(transaction, { customer, recipient }));

    if (!risk.requiresIntervention) {
      transaction.status = "COMPLETED";
      await this.providers.transactions.save(transaction);
      return {
        contractVersion: "1.0",
        institutionId: intent.institutionId,
        transactionId: transaction.id,
        outcome: "CONTINUE",
        transactionStatus: transaction.status,
        risk,
        intervention: null,
      };
    }

    await this.providers.transactions.save(transaction);
    const assessment = initialAssessment(risk);
    const caseCount = await this.providers.cases.count();
    const caseItem: InterventionCase = {
      id: `case_${crypto.randomUUID().slice(0, 8)}`,
      displayId: String(1042 + caseCount),
      customerId: intent.customerId,
      transactionId: transaction.id,
      institutionId: intent.institutionId,
      status: "OPEN",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      riskAnalysis: risk,
      messages: [
        {
          id: crypto.randomUUID(),
          role: "agent",
          content: `${assessment.customerExplanation} ${assessment.nextQuestion}`,
          createdAt: new Date().toISOString(),
        },
      ],
      assessment,
      employeeNotes: [],
      contextSnapshot: { customer, recipient },
    };
    await this.providers.cases.save(caseItem);
    console.info(
      `[Guardian integration] ${intent.institutionId} opened case ${caseItem.displayId} for ${intent.rail} transaction ${intent.transactionId}.`,
    );
    return {
      contractVersion: "1.0",
      institutionId: intent.institutionId,
      transactionId: transaction.id,
      outcome: "INTERVENE",
      transactionStatus: transaction.status,
      risk,
      intervention: {
        caseId: caseItem.id,
        displayId: caseItem.displayId,
        status: caseItem.status,
        sessionPath: `/intervention/${caseItem.id}`,
        firstMessage: caseItem.messages[0].content,
      },
    };
  }

  async addMessage(caseId: string, content: string) {
    const caseItem = await this.requireCase(caseId);
    if (isCaseClosed(caseItem.status)) throw new Error("CASE_CLOSED");
    const transaction = await this.providers.transactions.get(caseItem.transactionId);
    if (!transaction) throw new Error("TRANSACTION_NOT_FOUND");
    const { customer, recipient } = caseItem.contextSnapshot;

    recordCustomerAnswer(caseItem, content);
    const context = { caseItem, transaction, customer, recipient };
    const assessment = await assessWithGemini(caseItem, context);
    caseItem.assessment = assessment;

    const outcome =
      assessment.nextAction === "ASK_FOLLOW_UP" ? undefined : INTERVIEW_OUTCOMES[assessment.nextAction];
    if (outcome) {
      caseItem.status = outcome.caseStatus;
      if (outcome.resolution) caseItem.resolution = outcome.resolution;
      await this.providers.transactions.updateStatus(caseItem.transactionId, outcome.transactionStatus);
      transaction.status = outcome.transactionStatus;
      console.info(
        `[Guardian] Case ${caseItem.displayId} concluded as ${assessment.nextAction}; transaction ${caseItem.transactionId} is now ${outcome.transactionStatus}.`,
      );
    }

    caseItem.messages.push({
      id: crypto.randomUUID(),
      role: "agent",
      content: [assessment.customerExplanation, assessment.nextQuestion, outcome?.closing]
        .filter(Boolean)
        .join(" "),
      createdAt: new Date().toISOString(),
    });
    caseItem.updatedAt = new Date().toISOString();
    await this.providers.cases.save(caseItem);
    return caseItem;
  }

  async getCase(caseId: string) {
    return this.requireCase(caseId);
  }

  async getSummary(caseId: string) {
    const caseItem = await this.requireCase(caseId);
    const transaction = await this.providers.transactions.get(caseItem.transactionId);
    if (!transaction) throw new Error("TRANSACTION_NOT_FOUND");
    const { customer, recipient } = caseItem.contextSnapshot;
    return createCaseSummary({ caseItem, transaction, customer, recipient });
  }

  async applyHumanDecision(caseId: string, decision: GuardianDecision) {
    const caseItem = await this.requireCase(caseId);
    const at = new Date().toISOString();
    let status: TransactionStatus | undefined;
    if (decision.action === "MARK_REVIEWED") {
      caseItem.status = "REVIEWED";
    } else if (decision.action === "RELEASE") {
      caseItem.status = "RESOLVED";
      caseItem.resolution = "RELEASED";
      status = "RELEASED";
    } else if (decision.action === "KEEP_UNDER_REVIEW") {
      caseItem.status = "REVIEWED";
      caseItem.resolution = "UNDER_REVIEW";
      status = "UNDER_REVIEW";
    } else {
      caseItem.status = "RESOLVED";
      caseItem.resolution = "CANCELLED";
      status = "CANCELLED";
    }
    if (status) await this.providers.transactions.updateStatus(caseItem.transactionId, status);
    caseItem.employeeNotes.push(`${decision.action} by ${decision.decidedBy} at ${at}.`);
    caseItem.updatedAt = at;
    await this.providers.cases.save(caseItem);
    await this.providers.decisionNotifier.notify(caseItem, decision);
    return caseItem;
  }

  private async requireCase(caseId: string) {
    const caseItem = await this.providers.cases.get(caseId);
    if (!caseItem) throw new Error("CASE_NOT_FOUND");
    return caseItem;
  }
}
