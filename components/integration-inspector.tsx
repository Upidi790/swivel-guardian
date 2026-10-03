"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Send, Sparkles } from "@/components/icons";

const requestTemplate = {
  transaction: {
    institutionId: "partner_bank_sandbox",
    transactionId: "GENERATED_AT_RUNTIME",
    customerId: "customer_4821",
    rail: "WIRE",
    amount: 3750,
    currency: "USD",
    destination: { id: "vendor_new_19", label: "Capital Holdings Group", type: "BUSINESS" },
    channel: "MOBILE",
    deviceId: "customer_known_phone",
    region: "san_antonio",
    memo: "Secure account transfer",
    metadata: { bankExperience: "partner-mobile-app" },
  },
  customerContext: {
    customerId: "customer_4821",
    displayName: "Reference Customer",
    normalTransferMedian: 145,
    p95Transfer: 510,
    knownDeviceIds: ["customer_known_phone"],
    knownRegions: ["san_antonio"],
  },
  recipientContext: {
    destinationId: "vendor_new_19",
    displayName: "Capital Holdings Group",
    createdAt: "GENERATED_AT_RUNTIME",
    previousTransactionCount: 0,
    trustStatus: "UNVERIFIED",
  },
};

export function IntegrationInspector() {
  const [response, setResponse] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const displayRequest = useMemo(() => JSON.stringify(requestTemplate, null, 2), []);

  async function run() {
    setBusy(true); setError(""); setResponse(null);
    const now = new Date().toISOString();
    const request = structuredClone(requestTemplate);
    request.transaction.transactionId = `partner_txn_${crypto.randomUUID().slice(0, 8)}`;
    request.recipientContext.createdAt = now;
    try {
      const result = await fetch("/api/v1/transactions/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": request.transaction.transactionId },
        body: JSON.stringify(request),
      });
      const payload = await result.json();
      if (!result.ok) throw new Error(payload.message ?? "Integration request failed.");
      setResponse(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Integration request failed.");
    } finally {
      setBusy(false);
    }
  }

  const intervention = response?.intervention as { sessionPath?: string } | null | undefined;
  return (
    <section className="card inspector-card">
      <div className="card-header"><div><p className="eyebrow">Live contract inspector</p><h2>Call Guardian as a different bank</h2></div><button type="button" className="button-primary" onClick={run} disabled={busy}><Send size={14} /> {busy ? "Evaluating…" : "Run portable API demo"}</button></div>
      <div className="inspector-grid">
        <div><span className="code-label">REQUEST · PARTNER BANK</span><pre>{displayRequest}</pre></div>
        <div><span className="code-label">RESPONSE · GUARDIAN v1</span>{error ? <div className="error-box">{error}</div> : response ? <><pre>{JSON.stringify(response, null, 2)}</pre>{intervention?.sessionPath && <Link className="button-secondary inspector-link" href={intervention.sessionPath}><Sparkles size={14} /> Open returned intervention session</Link>}</> : <div className="response-placeholder"><Sparkles size={22} /><p>Run the request to prove the same agent accepts another institution, customer, rail, and UI channel.</p></div>}</div>
      </div>
    </section>
  );
}
