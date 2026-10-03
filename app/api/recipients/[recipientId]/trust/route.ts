import { NextResponse } from "next/server";
import { demoStore } from "@/lib/demo-store";

export async function POST(_: Request, { params }: { params: Promise<{ recipientId: string }> }) {
  const { recipientId } = await params;
  const state = demoStore.getState();
  const recipient = state.recipients.find((item) => item.id === recipientId);
  if (!recipient) return NextResponse.json({ error: "Recipient not found." }, { status: 404 });
  if (recipient.trustStatus === "TRUSTED") return NextResponse.json({ recipient });
  const updated = { ...recipient, trustStatus: "TRUST_REQUESTED" as const };
  demoStore.updateRecipient(updated);
  return NextResponse.json(
    { recipient: updated, message: "Verification request created. Employee approval and a second factor are required." },
    { status: 202 },
  );
}
