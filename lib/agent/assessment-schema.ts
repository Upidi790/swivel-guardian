import { z } from "zod";

export const agentAssessmentSchema = z.object({
  assessment: z.enum(["LOW_CONCERN", "NEEDS_CLARIFICATION", "HIGH_CONCERN"]),
  confidence: z.number().min(0).max(1),
  socialEngineeringSignals: z.array(z.string()).max(12),
  nextAction: z.enum(["ASK_FOLLOW_UP", "ALLOW", "REVIEW", "ESCALATE"]),
  customerExplanation: z.string().min(1).max(1_000),
  nextQuestion: z.string().max(500).nullable(),
  rationale: z.array(z.string()).max(8),
  employeeNotification: z.string().min(1).max(320).optional(),
});
