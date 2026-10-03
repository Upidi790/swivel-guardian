import { NextResponse } from "next/server";
import { z } from "zod";
import { demoStore } from "@/lib/demo-store";

/**
 * Simulated employee + second-factor approval of a customer's trust request.
 *
 * Trust is only reachable through this route, so a customer can never move a
 * recipient from UNVERIFIED straight to TRUSTED to escape an intervention.
 * This is the demo application's own surface, not part of the versioned
 * Guardian contract in docs/GUARDIAN_INTEGRATION.md.
 */
const trustDecisionSchema = z.object({
  action: z.enum(["APPROVE", "DENY"]),
  decidedBy: z.string().trim().min(1).max(80).default("alex_kim_demo"),
  secondFactorVerified: z.boolean().default(true),
});

export async function POST(request: Request, { params }: { params: Promise<{ recipientId: string }> }) {
  const { recipientId } = await params;
  let decision: z.infer<typeof trustDecisionSchema>;
  try {
    decision = trustDecisionSchema.parse(await request.json());
  } catch {
    return NextResponse.json({ error: "INVALID_DECISION" }, { status: 400 });
  }

  const recipient = demoStore.getState().recipients.find((item) => item.id === recipientId);
  if (!recipient) return NextResponse.json({ error: "RECIPIENT_NOT_FOUND" }, { status: 404 });
  if (recipient.trustStatus !== "TRUST_REQUESTED") {
    return NextResponse.json(
      { error: "NO_PENDING_TRUST_REQUEST", message: "Only a recipient the customer requested trust for can be decided." },
      { status: 409 },
    );
  }
  if (decision.action === "APPROVE" && !decision.secondFactorVerified) {
    return NextResponse.json(
      { error: "SECOND_FACTOR_REQUIRED", message: "Trust approval requires a verified second factor." },
      { status: 409 },
    );
  }

  const updated = {
    ...recipient,
    trustStatus: decision.action === "APPROVE" ? ("TRUSTED" as const) : ("UNVERIFIED" as const),
  };
  demoStore.updateRecipient(updated);
  console.info(
    `[SWIVEL Guardian] Trust ${decision.action} for ${recipientId} by ${decision.decidedBy} (second factor: ${decision.secondFactorVerified}).`,
  );
  return NextResponse.json({
    recipient: updated,
    message:
      decision.action === "APPROVE"
        ? "Trust approved after simulated employee review and a second factor."
        : "Trust request denied. The recipient stays unverified.",
  });
}
