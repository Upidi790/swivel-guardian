"use client";

import { useState } from "react";
import Link from "next/link";
import { Headphones, MessageCircle, Phone, ShieldCheck } from "@/components/icons";
import type { InterventionCase } from "@/lib/types";

export function SupportOptions({ initialCase }: { initialCase: InterventionCase }) {
  const [caseItem, setCaseItem] = useState(initialCase);
  const [busy, setBusy] = useState(false);

  async function requestSupport(request: "LIVE_CHAT" | "PHONE_CALL") {
    if (busy) return;
    setBusy(true);
    const response = await fetch(`/api/v1/cases/${caseItem.id}/support`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request }),
    });
    if (response.ok) setCaseItem((await response.json()).case);
    setBusy(false);
  }

  if (caseItem.supportStatus === "CALL_REQUESTED") return <section className="support-options call-requested"><Phone size={25} /><div><p className="eyebrow">Call requested</p><h2>A fraud specialist will contact you shortly.</h2><p>Keep this page open and do not send this payment another way. Your payment remains protected while the specialist reviews your Guardian case.</p></div></section>;
  if (caseItem.supportStatus === "QUEUED" || caseItem.supportStatus === "ASSIGNED") return <section className="support-options live-queued"><Headphones size={25} /><div><p className="eyebrow">Connecting secure support</p><h2>Connecting you with a Fraud Support Specialist</h2><p>Estimated wait: 2–5 minutes. Your Guardian case summary, payment details, and safety conversation have already been shared—you will not need to start over.</p><Link href="/employee/cases" className="text-link">Demo: view the specialist queue →</Link></div></section>;
  return <section className="support-options"><div className="support-alert-illustration" aria-hidden="true"><i className="support-spark spark-a" /><i className="support-spark spark-b" /><span className="support-lock"><ShieldCheck size={25} /></span><div className="support-device"><div><ShieldCheck size={34} /><strong>GUARDIAN ALERT</strong><small>PAYMENT PROTECTED</small></div><i /></div></div><div><p className="eyebrow">Payment protected</p><h2>Guardian has protected this payment.</h2><p>We found several warning signs associated with financial scams. Your payment has <strong>not</strong> been sent. Guardian recommends immediate human assistance.</p><div className="support-actions"><button className="button-primary" type="button" onClick={() => requestSupport("LIVE_CHAT")} disabled={busy}><MessageCircle size={16} /> {busy ? "Creating support case…" : "Start live chat"}</button><button className="button-secondary" type="button" onClick={() => requestSupport("PHONE_CALL")} disabled={busy}><Phone size={16} /> Request a phone call</button></div><small>Estimated specialist wait: under 5 minutes · simulated for this demo</small></div></section>;
}
