"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { BadgeCheck, Clock3 } from "@/components/icons";
import { formatDate } from "@/lib/format";
import type { Recipient } from "@/lib/types";

/**
 * Employee-side half of the trusted-recipient workflow. A customer can only
 * request trust; TRUSTED is reachable only through this simulated review plus
 * a second factor, so trust can never be used to bypass an intervention.
 */
export function TrustRequests({ requests }: { requests: Recipient[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function decide(id: string, action: "APPROVE" | "DENY") {
    setBusy(`${id}:${action}`);
    setError("");
    try {
      const response = await fetch(`/api/recipients/${id}/trust-decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, decidedBy: "alex_kim_demo", secondFactorVerified: true }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message ?? payload.error ?? "Decision failed.");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed.");
    } finally {
      setBusy("");
    }
  }

  if (!requests.length) return null;

  return (
    <div className="card table-card">
      <div className="card-header">
        <h2>
          <Clock3 size={14} style={{ display: "inline", marginRight: 6 }} />
          Trust verification requests
        </h2>
        <span className="subtitle">Customer requested · employee + second factor required</span>
      </div>
      <div className="section-body">
        {error && (
          <div className="error-box" role="alert">
            {error}
          </div>
        )}
        {requests.map((recipient) => (
          <div className="trust-request-row" key={recipient.id}>
            <div>
              <strong>{recipient.name}</strong>
              <div className="subtitle">
                {recipient.relationship} · added {formatDate(recipient.createdAt)} ·{" "}
                {recipient.previousTransactionCount} previous payments
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                className="button-primary"
                disabled={Boolean(busy)}
                onClick={() => decide(recipient.id, "APPROVE")}
              >
                <BadgeCheck size={13} />
                {busy === `${recipient.id}:APPROVE` ? "Approving…" : "Approve trust"}
              </button>
              <button
                type="button"
                className="button-quiet"
                disabled={Boolean(busy)}
                onClick={() => decide(recipient.id, "DENY")}
              >
                {busy === `${recipient.id}:DENY` ? "Denying…" : "Deny"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
