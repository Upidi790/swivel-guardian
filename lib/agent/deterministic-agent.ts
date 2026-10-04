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
    ? `This payment is a little different from your usual activity: ${riskSignals
        .slice(0, 2)
        .map((signal) => signal.explanation.replace(/[.!]$/, "").toLowerCase())}.`
    : "This payment is a little different from your usual activity.";
  const normalSummary = normalSignals.length
    ? " This is a quick safety check, not an accusation—you can share only what feels comfortable."
    : " This is a quick safety check, and you can share only what feels comfortable.";
  return {
    assessment: "NEEDS_CLARIFICATION",
    confidence: 0.62,
    socialEngineeringSignals: [],
    nextAction: "ASK_FOLLOW_UP",
    customerExplanation: `${riskSummary}${normalSummary}`,
    nextQuestion: "Was this payment your idea, or did someone ask you to send it?",
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
      customerExplanation: "Thanks for confirming. Because this is a new recipient and a larger-than-usual payment, one small detail will help us keep it safe.",
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
      customerExplanation: "Thanks for sharing that. Someone else being involved is useful context; it does not mean anything is wrong.",
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
      customerExplanation: "That sounds like a reasonable explanation, and you have not described pressure, threats, or secrecy. Because this is a new payment destination, a specialist will do one brief verification. Once it is confirmed, you can request trusted-recipient verification for future payments—nothing is added automatically.",
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
