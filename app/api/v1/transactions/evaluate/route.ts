import { getGuardianService, guardianEvaluateRequestSchema } from "@/lib/guardian";
import {
  authorizeGuardianRequest,
  guardianError,
  guardianJson,
  guardianOptionsResponse,
  rejectOversizedRequest,
  rejectUnauthorized,
} from "@/lib/guardian/http";

export function OPTIONS() {
  return guardianOptionsResponse();
}

export async function POST(request: Request) {
  if (!authorizeGuardianRequest(request)) return rejectUnauthorized();
  if (rejectOversizedRequest(request)) return guardianJson({ error: "PAYLOAD_TOO_LARGE" }, { status: 413 });
  try {
    const input = guardianEvaluateRequestSchema.parse(await request.json());
    const result = await getGuardianService().evaluate(input);
    return guardianJson(result, { status: result.outcome === "INTERVENE" ? 202 : 200 });
  } catch (error) {
    console.error("[Guardian API] Transaction evaluation failed.", error);
    return guardianError(error);
  }
}
