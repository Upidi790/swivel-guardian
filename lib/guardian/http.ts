import { NextResponse } from "next/server";

export function guardianCorsHeaders() {
  return {
    "Access-Control-Allow-Origin": process.env.GUARDIAN_ALLOWED_ORIGIN ?? "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Idempotency-Key",
    "Cache-Control": "no-store",
    Vary: "Origin",
  };
}

export function guardianOptionsResponse() {
  return new NextResponse(null, { status: 204, headers: guardianCorsHeaders() });
}

export function authorizeGuardianRequest(request: Request) {
  const configuredKey = process.env.GUARDIAN_API_KEY;
  if (!configuredKey) return true;
  return request.headers.get("authorization") === `Bearer ${configuredKey}`;
}

export function guardianJson(data: unknown, init?: { status?: number }) {
  return NextResponse.json(data, { ...init, headers: guardianCorsHeaders() });
}

export function guardianError(error: unknown) {
  const code = error instanceof Error ? error.message : "UNKNOWN_ERROR";
  const status = code.includes("NOT_FOUND") ? 404 : code === "CASE_CLOSED" || code === "TRANSACTION_ALREADY_EVALUATED" ? 409 : 400;
  return guardianJson({ error: code, message: "Guardian could not process this request." }, { status });
}

export function rejectUnauthorized() {
  return guardianJson({ error: "UNAUTHORIZED", message: "A valid Guardian API credential is required." }, { status: 401 });
}

export function rejectOversizedRequest(request: Request) {
  const length = Number(request.headers.get("content-length") ?? 0);
  return length > 64_000;
}
