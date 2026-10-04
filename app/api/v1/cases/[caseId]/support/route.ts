import { NextResponse } from "next/server";
import { z } from "zod";
import { demoStore } from "@/lib/demo-store";

const supportRequestSchema = z.object({ request: z.enum(["LIVE_CHAT", "PHONE_CALL"]) });

export async function POST(request: Request, { params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  const parsed = supportRequestSchema.safeParse(await request.json());
  if (!parsed.success) return NextResponse.json({ error: "Invalid support request." }, { status: 400 });
  const caseItem = demoStore.requestSupport(caseId, parsed.data.request);
  if (!caseItem) return NextResponse.json({ error: "Case not found." }, { status: 404 });
  return NextResponse.json({ case: caseItem });
}
