import { NextResponse } from "next/server";
import { demoStore } from "@/lib/demo-store";

export async function POST() {
  const state = demoStore.reset();
  console.info("[SWIVEL Guardian] Demo state reset.");
  return NextResponse.json({ ok: true, state });
}
