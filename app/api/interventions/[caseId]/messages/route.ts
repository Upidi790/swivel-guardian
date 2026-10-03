import { NextResponse } from "next/server";
import { addCustomerMessage } from "@/lib/services/intervention-service";
import { messageRequestSchema } from "@/lib/validation";

export async function POST(request: Request, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    const { message } = messageRequestSchema.parse(await request.json());
    const caseItem = await addCustomerMessage(caseId, message);
    return NextResponse.json({ case: caseItem });
  } catch (error) {
    const message = error instanceof Error ? error.message : "UNKNOWN";
    const status = message === "CASE_NOT_FOUND" ? 404 : message === "CASE_CLOSED" ? 409 : 400;
    return NextResponse.json(
      { error: message === "CASE_CLOSED" ? "This interview is complete and awaiting a human decision." : "We couldn't save that answer. Please try again." },
      { status },
    );
  }
}
