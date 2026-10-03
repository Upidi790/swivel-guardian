"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "@/components/icons";

export function ResetDemoButton() {
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  async function reset() {
    setBusy(true);
    await fetch("/api/demo/reset", { method: "POST" });
    router.push("/dashboard");
    router.refresh();
    setBusy(false);
  }
  return (
    <button type="button" className="reset-button" onClick={reset} disabled={busy} aria-label="Reset demo state">
      <RefreshCw size={15} className={busy ? "spin" : ""} />
      <span>{busy ? "Resetting" : "Reset demo"}</span>
    </button>
  );
}
