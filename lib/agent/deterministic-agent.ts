import { searchScamPatterns } from "@/lib/agent/tools";
import type { AgentAssessment, InterventionCase } from "@/lib/types";

function detectedSignals(caseItem: InterventionCase): string[] {
  const customerMessages = caseItem.messages.filter((message) => message.role === "customer");
  const text = customerMessages.map((message) => message.content).join(" ");
  const signals = new Set(searchScamPatterns(text).map((pattern) => pattern.id));
  const first = customerMessages[0]?.content.toLowerCase() ?? "";
  if (/^(yes|yeah|yep|someone did)/.test(first)) signals.add("EXTERNAL_INSTRUCTION");
  if (/don'?t tell|do not tell|not to tell (?:my )?bank|keep (?:it|this) secret/.test(text)) signals.add("SECRECY_REQUEST");
  if (/^(no|nope|nobody)/.test(first)) signals.delete("EXTERNAL_INSTRUCTION");
  if (/no rush|not urgent|take my time/.test(text)) signals.delete("URGENCY");
  if (/nobody[^.]*secret|no one[^.]*secret|not (?:asked|told)[^.]*secret|didn'?t[^.]*secret/.test(text)) signals.delete("SECRECY_REQUEST");
  return [...signals];
}

export function initialAssessment(riskAnalysis?: InterventionCase["riskAnalysis"]): AgentAssessment {
  const riskSignals = riskAnalysis?.signals.filter((signal) => signal.category === "RISK") ?? [];
  const normalSignals = riskAnalysis?.signals.filter((signal) => signal.category === "NORMAL") ?? [];
  const riskSummary = riskSignals.length
    ? `This payment differs from the customer's normal activity: ${riskSignals
        .slice(0, 2)
        .map((signal) => signal.explanation.replace(/[.!]$/, "").toLowerCase())
        .join("; ")}.`
    : "This payment differs from the customer's normal activity.";
  const normalSummary = normalSignals.length
    ? " Some identity and access indicators still look normal, so we need to understand the reason for the payment."
    : " We need to understand the reason for the payment.";
  return {
    assessment: "NEEDS_CLARIFICATION",
    confidence: 0.62,
    socialEngineeringSignals: [],
    nextAction: "ASK_FOLLOW_UP",
    customerExplanation: `${riskSummary}${normalSummary}`,
    nextQuestion: "Did someone contact you and ask you to make this payment?",
    rationale: ["New recipient", "Amount far above normal", "Known device and normal region"],
    modelSource: "deterministic-fallback",
  };
}

export function runDeterministicAgent(caseItem: InterventionCase): AgentAssessment {
  const answers = caseItem.messages.filter((message) => message.role === "customer");
  const signals = detectedSignals(caseItem);
  const allText = answers.map((message) => message.content.toLowerCase()).join(" ");
  const highConcern =
    signals.includes("AUTHORITY_IMPERSONATION") &&
    ["THREAT", "URGENCY", "SECRECY_REQUEST"].some((signal) => signals.includes(signal));

  if (highConcern || signals.includes("SECRECY_REQUEST") && signals.includes("THREAT")) {
    return {
      assessment: "HIGH_CONCERN",
      confidence: 0.94,
      socialEngineeringSignals: signals,
      nextAction: "ESCALATE",
      customerExplanation:
        "Several details you described—an authority claim, pressure or threats, and a request for secrecy—are common warning signs of an impersonation scam. The payment will stay pending while a bank employee reviews it with you.",
      nextQuestion: null,
      rationale: signals.map((signal) => `Customer statement matched ${signal.replaceAll("_", " ").toLowerCase()}.`),
      modelSource: "deterministic-fallback",
    };
  }

  if (answers.length === 1 && /^(no|nope|nobody)/.test(answers[0].content.toLowerCase())) {
    return {
      assessment: "NEEDS_CLARIFICATION",
      confidence: 0.68,
      socialEngineeringSignals: [],
      nextAction: "ASK_FOLLOW_UP",
      customerExplanation: "Thanks. We still need to verify why this unusually large payment is going to a new recipient.",
      nextQuestion: "What is the payment for, and how do you know the recipient?",
      rationale: ["No third-party instruction disclosed", "Behavioral anomaly still requires verification"],
      modelSource: "deterministic-fallback",
    };
  }

  if (answers.length === 1) {
    return {
      assessment: "NEEDS_CLARIFICATION",
      confidence: 0.76,
      socialEngineeringSignals: signals.length ? signals : ["EXTERNAL_INSTRUCTION"],
      nextAction: "ASK_FOLLOW_UP",
      customerExplanation: "Thank you. A request from another person can be important context for an unusual payment.",
      nextQuestion: "How did they contact you, and what did they say the payment was for?",
      rationale: ["Customer acknowledged contact or instruction from another person"],
      modelSource: "deterministic-fallback",
    };
  }

  if (answers.length === 2 && (signals.includes("AUTHORITY_IMPERSONATION") || signals.includes("BANK_IMPERSONATION"))) {
    return {
      assessment: "NEEDS_CLARIFICATION",
      confidence: 0.86,
      socialEngineeringSignals: signals,
      nextAction: "ASK_FOLLOW_UP",
      customerExplanation: "People impersonating trusted organizations sometimes use fear or pressure to make payments feel unavoidable.",
      nextQuestion: "Did they say you had to act immediately, threaten a consequence, or tell you not to speak with your bank or family?",
      rationale: ["Customer described an apparent authority or bank representative", "Urgency, threat, and secrecy remain unconfirmed"],
      modelSource: "deterministic-fallback",
    };
  }

  const looksLegitimate = /tuition|rent|invoice|contractor|daughter|family/.test(allText) && !signals.some((s) => ["THREAT", "URGENCY", "SECRECY_REQUEST"].includes(s));
  if (looksLegitimate && answers.length >= 2) {
    return {
      assessment: "LOW_CONCERN",
      confidence: 0.78,
      socialEngineeringSignals: signals.filter((signal) => signal !== "EXTERNAL_INSTRUCTION"),
      nextAction: "REVIEW",
      customerExplanation: "Your explanation does not contain common pressure, threat, or secrecy indicators. Because the amount and recipient are still unusual, a brief verification is recommended.",
      nextQuestion: null,
      rationale: ["Plausible payment purpose", "No urgency, threat, or secrecy disclosed", "Behavioral anomaly remains"],
      modelSource: "deterministic-fallback",
    };
  }

  return {
    assessment: "NEEDS_CLARIFICATION",
    confidence: 0.7,
    socialEngineeringSignals: signals,
    nextAction: "ASK_FOLLOW_UP",
    customerExplanation: "I need one more detail to understand whether anyone is pressuring or directing this payment.",
    nextQuestion: "What would happen if you did not send this payment today, and has anyone asked you to keep it secret?",
    rationale: ["Purpose and pressure indicators remain unclear"],
    modelSource: "deterministic-fallback",
  };
}
