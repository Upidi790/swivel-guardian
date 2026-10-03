import { describe, expect, it } from "vitest";
import { initialAssessment, runDeterministicAgent } from "@/lib/agent/deterministic-agent";
import type { ChatMessage, InterventionCase } from "@/lib/types";

const customerMessage = (content: string): ChatMessage => ({
  id: crypto.randomUUID(), role: "customer", content, createdAt: new Date().toISOString(),
});

function caseWith(messages: ChatMessage[]): InterventionCase {
  return {
    id: "case_test", displayId: "1042", customerId: "maria_001", transactionId: "txn_test", status: "OPEN",
    createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), messages, assessment: initialAssessment(), employeeNotes: [],
    riskAnalysis: {
      transactionId: "txn_test", riskScore: 82, riskLevel: "HIGH", requiresIntervention: true, provider: "mock",
      signals: [], baseline: { medianTransfer: 120, p95Transfer: 430, previousRecipientTransactions: 0 },
    },
    contextSnapshot: {
      customer: {
        customerId: "maria_001", displayName: "Maria Rodriguez", normalTransferMedian: 120, p95Transfer: 430,
        knownDeviceIds: ["iphone_maria"], knownRegions: ["san_antonio"],
      },
      recipient: {
        destinationId: "recipient_secure", displayName: "Secure Asset Services", createdAt: new Date().toISOString(),
        previousTransactionCount: 0, trustStatus: "UNVERIFIED",
      },
    },
  };
}

describe("deterministic intervention agent", () => {
  it("escalates government impersonation with threat and secrecy on a safe device scenario", () => {
    const assessment = runDeterministicAgent(caseWith([
      customerMessage("Yes."),
      customerMessage("They called and said they were from the government."),
      customerMessage("They said I could be arrested and told me not to tell my bank."),
    ]));
    expect(assessment.nextAction).toBe("ESCALATE");
    expect(assessment.socialEngineeringSignals).toEqual(expect.arrayContaining(["AUTHORITY_IMPERSONATION", "THREAT", "SECRECY_REQUEST"]));
  });

  it("recommends review for unusual but plausible tuition without coercion", () => {
    const assessment = runDeterministicAgent(caseWith([
      customerMessage("No, nobody asked me."),
      customerMessage("This is tuition for my daughter. There is no rush and nobody told me to keep it secret."),
    ]));
    expect(assessment.nextAction).toBe("REVIEW");
    expect(assessment.assessment).toBe("LOW_CONCERN");
  });

  it("asks an adaptive follow-up after external contact is disclosed", () => {
    const assessment = runDeterministicAgent(caseWith([customerMessage("Yes.")]));
    expect(assessment.nextAction).toBe("ASK_FOLLOW_UP");
    expect(assessment.nextQuestion).toMatch(/How did they contact/i);
  });
});
