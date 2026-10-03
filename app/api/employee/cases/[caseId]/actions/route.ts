import { NextResponse } from "next/server";
import { getGuardianService } from "@/lib/guardian";
import { employeeActionSchema } from "@/lib/validation";

export async function POST(request: Request, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    const { action } = employeeActionSchema.parse(await request.json());
    const caseItem = await getGuardianService().applyHumanDecision(caseId, { action, decidedBy: "legacy_employee_route" });
    console.info(`[SWIVEL Guardian] Employee action ${action} applied to case ${caseItem.displayId}.`);
    return NextResponse.json({ case: caseItem });
  } catch (error) {
    console.error("[SWIVEL Guardian] Employee action failed.", error);
    return NextResponse.json({ error: "The simulated action could not be completed." }, { status: 400 });
  }
}
