"use client";

import { useState } from "react";
import Link from "next/link";
import { BadgeCheck, Clock3, Send } from "@/components/icons";
import { StatusBadge } from "@/components/status-badge";
import { formatDate } from "@/lib/format";
import type { Recipient } from "@/lib/types";

export function RecipientCards({ initialRecipients }: { initialRecipients: Recipient[] }) {
  const [recipients, setRecipients] = useState(initialRecipients);
  const [notice, setNotice] = useState("");
  async function requestTrust(id: string) {
    const response = await fetch(`/api/recipients/${id}/trust`, { method: "POST" });
    const payload = await response.json();
    if (response.ok) {
      setRecipients((current) => current.map((item) => item.id === id ? { ...item, trustStatus: "TRUST_REQUESTED" } : item));
      setNotice(payload.message ?? "Verification requested.");
    }
  }
  return <>
    {notice && <div className="trust-callout"><Clock3 size={17} />{notice}</div>}
    <div className="recipient-grid">
      {recipients.map((recipient) => <article className="card recipient-card" key={recipient.id}>
        <div className="recipient-card-top"><span className="avatar">{recipient.name.split(" ").map((s) => s[0]).join("").slice(0,2)}</span><StatusBadge status={recipient.trustStatus} /></div>
        <h3>{recipient.name}</h3><p>{recipient.relationship}</p>
        <div style={{ display: "flex", gap: 8 }}><Link className="button-secondary" style={{ flex: 1, padding: 8 }} href={`/send?recipient=${recipient.id}`}><Send size={13} /> Pay</Link>
          {recipient.trustStatus === "UNVERIFIED" && <button type="button" className="button-quiet" style={{ flex: 1, padding: 8 }} onClick={() => requestTrust(recipient.id)}><BadgeCheck size={13} /> Request trust</button>}
        </div>
        <div className="recipient-meta"><span>Added {formatDate(recipient.createdAt)}</span><span>{recipient.previousTransactionCount} payments</span></div>
      </article>)}
    </div>
  </>;
}
