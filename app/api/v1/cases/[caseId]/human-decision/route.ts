import { getGuardianService, guardianDecisionRequestSchema } from "@/lib/guardian";
import { authorizeGuardianRequest, guardianError, guardianJson, guardianOptionsResponse, rejectUnauthorized } from "@/lib/guardian/http";

export function OPTIONS() {
  return guardianOptionsResponse();
}

export async function POST(request: Request, { params }: { params: Promise<{ caseId: string }> }) {
  if (!authorizeGuardianRequest(request)) return rejectUnauthorized();
  try {
    const { caseId } = await params;
    const decision = guardianDecisionRequestSchema.parse(await request.json());
    const caseItem = await getGuardianService().applyHumanDecision(caseId, decision);
    return guardianJson({ contractVersion: "1.0", case: caseItem });
  } catch (error) {
    return guardianError(error);
  }
}
