"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Check, LockKeyhole, MessageCircle, Send, ShieldEllipsis, TriangleAlert } from "@/components/icons";
import { StatusBadge } from "@/components/status-badge";
import { formatCurrency, formatDateTime } from "@/lib/format";
import type { InterventionCase, Transaction } from "@/lib/types";

const quickReplies = ["Yes", "No", "They called me and said they were from the government.", "They threatened arrest and told me not to tell my bank."];

export function InterventionExperience({ initialCase, transaction }: { initialCase: InterventionCase; transaction: Transaction }) {
  const [caseItem, setCaseItem] = useState(initialCase);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef<HTMLDivElement>(null);
  const closed = caseItem.status === "ESCALATED" || caseItem.status === "RESOLVED";
  const messageCount = caseItem.messages.length;

  useEffect(() => { void messageCount; void busy; messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" }); }, [messageCount, busy]);

  async function send(content = message) {
    if (!content.trim() || busy || closed) return;
    setMessage(""); setBusy(true); setError("");
    try {
      const response = await fetch(`/api/v1/cases/${caseItem.id}/messages`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: content }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error ?? "Answer could not be saved.");
      setCaseItem(payload.case);
    } catch (err) { setError(err instanceof Error ? err.message : "Answer could not be saved."); }
    finally { setBusy(false); }
  }

  return <div className="intervention-page"><div className="intervention-wrap">
    <div className="intervention-top">
      <div className="intervention-title"><div className="guardian-icon"><ShieldEllipsis size={24} /></div><div><p className="eyebrow">Payment check</p><h1>Let&apos;s make sure this payment is safe.</h1><p className="subtitle">Your payment is paused—not declined—while we learn a little more.</p></div></div>
      <StatusBadge status={caseItem.status === "ESCALATED" ? "Awaiting human review" : "Payment paused"} />
    </div>
    <div className="intervention-grid">
      <section className="card chat-card">
        <div className="chat-header"><div className="agent-presence"><div className="agent-dot"><MessageCircle size={17} /></div><div><strong>Guardian assistant</strong><small>● Secure conversation</small></div></div></div>
        <div className="messages" ref={messagesRef} aria-live="polite">
          {caseItem.messages.map((item) => <div className={`message ${item.role}`} key={item.id}><div><div className="message-bubble">{item.content}</div><time>{formatDateTime(item.createdAt)}</time></div></div>)}
          {busy && <div className="message"><div className="message-bubble typing" role="status" aria-label="Guardian is thinking"><i /><i /><i /></div></div>}
        </div>
        {error && <div className="error-box" style={{ margin: "0 15px 10px" }}>{error}</div>}
        {closed ? <div className="escalation-banner"><strong>Human review requested.</strong> Your payment remains pending. A bank employee—not the AI—will make the final decision. <Link className="text-link" href="/employee/cases">Open demo employee queue →</Link></div> : <>
          <div className="quick-replies">{quickReplies.slice(caseItem.messages.filter((m) => m.role === "customer").length, caseItem.messages.filter((m) => m.role === "customer").length + 2).map((reply) => <button type="button" key={reply} onClick={() => send(reply)}>{reply}</button>)}</div>
          <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(); }}><textarea aria-label="Your answer" placeholder="Type your answer…" value={message} onChange={(e) => setMessage(e.target.value)} disabled={busy} /><button type="submit" disabled={busy || !message.trim()} aria-label="Send answer"><Send size={17} /></button></form>
        </>}
      </section>
      <aside className="case-sidebar">
        <div className="card side-card"><h3>Payment summary</h3><div className="payment-summary"><div><strong>{formatCurrency(transaction.amount)}</strong><small>to {transaction.recipientName}</small></div><StatusBadge status="Pending" /></div><div className="risk-meter"><span style={{ width: `${caseItem.riskAnalysis.riskScore}%` }} /></div><div className="risk-score-line"><span>Behavioral risk</span><strong>{caseItem.riskAnalysis.riskScore} / 100</strong></div></div>
        <div className="card side-card evidence-side"><h3><TriangleAlert size={15} /> Why we checked</h3><ul className="evidence-list">{caseItem.riskAnalysis.signals.map((signal) => <li key={signal.type}>{signal.category === "NORMAL" ? <Check className="normal-icon" size={14} /> : <TriangleAlert className="risk-icon" size={14} />}<span><strong>{signal.type.replaceAll("_", " ")}</strong><br />{signal.explanation}</span></li>)}</ul></div>
        <div className="card side-card privacy-card"><h3><LockKeyhole size={14} /> Your privacy</h3><p>Guardian only uses account activity and what you choose to share here. It cannot access your texts, email, or calls.</p></div>
      </aside>
    </div>
  </div></div>;
}
