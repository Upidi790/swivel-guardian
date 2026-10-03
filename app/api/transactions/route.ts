import { NextResponse } from "next/server";
import { createPayment } from "@/lib/services/transaction-service";
import { transactionRequestSchema } from "@/lib/validation";

export async function POST(request: Request) {
  try {
    const input = transactionRequestSchema.parse(await request.json());
    const result = await createPayment(input);
    return NextResponse.json(result, { status: result.outcome === "INTERVENTION" ? 202 : 201 });
  } catch (error) {
    console.error("[SWIVEL Guardian] Payment request failed.", error);
    return NextResponse.json({ error: "We couldn't process that payment. Please review the details and try again." }, { status: 400 });
  }
}
