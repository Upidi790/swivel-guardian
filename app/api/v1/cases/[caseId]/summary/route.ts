import { getGuardianService } from "@/lib/guardian";
import { authorizeGuardianRequest, guardianError, guardianJson, guardianOptionsResponse, rejectUnauthorized } from "@/lib/guardian/http";

export function OPTIONS() {
  return guardianOptionsResponse();
}

export async function GET(request: Request, { params }: { params: Promise<{ caseId: string }> }) {
  if (!authorizeGuardianRequest(request)) return rejectUnauthorized();
  try {
    const { caseId } = await params;
    return guardianJson({ contractVersion: "1.0", summary: await getGuardianService().getSummary(caseId) });
  } catch (error) {
    return guardianError(error);
  }
}
