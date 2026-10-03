import patterns from "@/data/scam_patterns.json";
import { agentAssessmentSchema } from "@/lib/agent/assessment-schema";
import { runDeterministicAgent } from "@/lib/agent/deterministic-agent";
import { AGENT_SYSTEM_PROMPT, buildAgentContext } from "@/lib/agent/prompt";
import type { AgentToolContext } from "@/lib/agent/tools";
import type { AgentAssessment, InterventionCase } from "@/lib/types";

const responseSchema = {
  type: "OBJECT",
  required: ["assessment", "confidence", "socialEngineeringSignals", "nextAction", "customerExplanation", "nextQuestion", "rationale"],
  properties: {
    assessment: { type: "STRING", enum: ["LOW_CONCERN", "NEEDS_CLARIFICATION", "HIGH_CONCERN"] },
    confidence: { type: "NUMBER", minimum: 0, maximum: 1 },
    socialEngineeringSignals: { type: "ARRAY", items: { type: "STRING", enum: patterns.map((pattern) => pattern.id) } },
    nextAction: { type: "STRING", enum: ["ASK_FOLLOW_UP", "ALLOW", "REVIEW", "ESCALATE"] },
    customerExplanation: { type: "STRING" },
    nextQuestion: { type: "STRING", nullable: true },
    rationale: { type: "ARRAY", items: { type: "STRING" } },
  },
};

export async function assessWithGemini(caseItem: InterventionCase, context: AgentToolContext): Promise<AgentAssessment> {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    // Announced rather than silent: the demo must never look like a live model
    // call succeeded when no credential was configured.
    console.warn("[SWIVEL Guardian] GEMINI_API_KEY is not set; using the deterministic agent fallback.");
    return runDeterministicAgent(caseItem);
  }
  try {
    const model = process.env.GEMINI_MODEL ?? "gemini-3.5-flash-lite";
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: AGENT_SYSTEM_PROMPT }] },
          contents: [{ role: "user", parts: [{ text: buildAgentContext(context) }] }],
          generationConfig: {
            temperature: 0.25,
            responseMimeType: "application/json",
            responseSchema,
          },
        }),
        signal: AbortSignal.timeout(8_000),
        cache: "no-store",
      },
    );
    if (!response.ok) throw new Error(`Gemini returned HTTP ${response.status}`);
    const payload = await response.json();
    const text = payload?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (typeof text !== "string") throw new Error("Gemini response did not contain structured text");
    const parsed = agentAssessmentSchema.parse(JSON.parse(text));
    return { ...parsed, modelSource: "gemini" };
  } catch (error) {
    console.warn("[SWIVEL Guardian] Gemini unavailable or malformed; using deterministic agent fallback.", error);
    return runDeterministicAgent(caseItem);
  }
}
