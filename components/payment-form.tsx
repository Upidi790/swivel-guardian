"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Send } from "@/components/icons";
import type { Recipient } from "@/lib/types";

const paymentDefaults: Record<string, { amount: string; memo: string }> = {
  recipient_elena: { amount: "95", memo: "Dinner" },
  recipient_college: { amount: "4800", memo: "Fall tuition" },
  recipient_secure: { amount: "2000", memo: "Account protection" },
  recipient_protection: { amount: "3250", memo: "Account security" },
};

export function PaymentForm({
  recipients,
  customer,
}: {
  recipients: Recipient[];
  customer: { id: string; deviceId: string; region: string };
}) {
  const search = useSearchParams();
  const router = useRouter();
  const defaultRecipient = search.get("recipient") ?? "recipient_secure";
  const [recipientId, setRecipientId] = useState(defaultRecipient);
  const [amount, setAmount] = useState(paymentDefaults[defaultRecipient]?.amount ?? "");
  const [memo, setMemo] = useState(paymentDefaults[defaultRecipient]?.memo ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const recipient = useMemo(() => recipients.find((item) => item.id === recipientId), [recipientId, recipients]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!recipient) return;
    setBusy(true); setError("");
    try {
      const transactionId = `txn_${crypto.randomUUID().slice(0, 8)}`;
      const response = await fetch("/api/v1/transactions/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transaction: {
            institutionId: "guardian_demo_credit_union",
            transactionId,
            customerId: customer.id,
            rail: "P2P",
            amount: Number(amount),
            currency: "USD",
            destination: {
              id: recipient.id,
              label: recipient.name,
              type: recipient.relationship === "Daughter" ? "PERSON" : "BUSINESS",
            },
            channel: "WEB",
            deviceId: customer.deviceId,
            region: customer.region,
            memo,
            metadata: { client: "reference-credit-union" },
          },
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error ?? "Payment failed.");
      if (result.outcome === "INTERVENE") router.push(result.intervention.sessionPath);
      else router.push(`/transactions?sent=1`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment failed.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      {error && <div className="error-box" role="alert">{error}</div>}
      <div className="field">
        <label htmlFor="recipient">Recipient</label>
        <select id="recipient" value={recipientId} onChange={(e) => { const nextRecipient = e.target.value; const defaults = paymentDefaults[nextRecipient]; setRecipientId(nextRecipient); setAmount(defaults?.amount ?? ""); setMemo(defaults?.memo ?? ""); }}>
          {recipients.map((item) => <option value={item.id} key={item.id}>{item.name} — {item.relationship}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="amount">Amount</label>
        <div className="amount-input"><span>$</span><input id="amount" type="number" min="0.01" step="0.01" max="1000000" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" required /></div>
      </div>
      <div className="field">
        <label htmlFor="memo">Memo <span style={{ color: "#8a94a5", fontWeight: 500 }}>(optional)</span></label>
        <input id="memo" value={memo} maxLength={140} onChange={(e) => setMemo(e.target.value)} placeholder="What's this for?" />
      </div>
      {recipient && <div className="trust-callout"><span className="avatar">{recipient.name.slice(0, 2).toUpperCase()}</span><div><strong style={{ display: "block", color: "#253b58" }}>{recipient.trustStatus === "TRUSTED" ? "Trusted recipient" : "New or unverified recipient"}</strong>{recipient.previousTransactionCount ? `${recipient.previousTransactionCount} previous payments` : "No previous payments from this account"}</div></div>}
      <div className="form-actions"><button className="button-secondary" type="button" onClick={() => router.back()}>Cancel</button><button className="button-primary" disabled={busy} type="submit"><Send size={15} />{busy ? "Checking payment…" : "Review & send"}</button></div>
    </form>
  );
}
