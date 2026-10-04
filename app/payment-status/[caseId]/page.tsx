import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { Check, Clock3, LockKeyhole, ShieldCheck, TriangleAlert } from "@/components/icons";
import { StatusBadge } from "@/components/status-badge";
import { demoStore } from "@/lib/demo-store";
import { formatCurrency } from "@/lib/format";

export const dynamic = "force-dynamic";

function outcomeFor(resolution: string | undefined) {
  if (resolution === "CANCELLED") {
    return {
      icon: TriangleAlert,
      tone: "protective",
      eyebrow: "Payment stopped for your protection",
      title: "We cancelled this payment before money left your account.",
      description: "Our team found signs that someone may have been pressuring you. A specialist can help you review what happened and stay safe.",
      next: "If someone contacted you about this payment, do not send money or share codes. Contact your bank using a number you trust.",
    };
  }
  if (resolution === "RELEASED") {
    return {
      icon: Check,
      tone: "approved",
      eyebrow: "Payment approved after human review",
      title: "Your payment has been released.",
      description: "A bank specialist reviewed the payment and confirmed it can proceed. Your activity remains protected by ongoing account monitoring.",
      next: "If any details change or someone asks you to send another payment, contact us before taking action.",
    };
  }
  return {
    icon: Clock3,
    tone: "review",
    eyebrow: "Specialist review in progress",
    title: "Your payment is still under review.",
    description: "Your money has not been sent. A bank specialist is reviewing the information you shared and will help with the next step.",
    next: "Please do not send the payment another way while the review is open.",
  };
}

export default async function PaymentStatusPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  const caseItem = demoStore.getCase(caseId);
  if (!caseItem) notFound();
  const transaction = demoStore.getTransaction(caseItem.transactionId);
  if (!transaction) notFound();
  const outcome = outcomeFor(caseItem.resolution);
  const Icon = outcome.icon;

  return <AppShell><div className="customer-status-page"><div className="customer-status-wrap">
    <nav className="journey-steps" aria-label="Payment safety journey">
      <span className="complete"><b>1</b><span className="journey-label">Payment started</span></span><i /><span className="complete"><b>2</b><span className="journey-label">Safety check</span></span><i /><span className="complete"><b>3</b><span className="journey-label">Specialist review</span></span><i /><span className="current"><b>4</b><span className="journey-label">Outcome</span></span>
    </nav>
    <section className={`customer-outcome-card ${outcome.tone}`}>
      <div className="customer-outcome-icon"><Icon size={27} /></div>
      <p className="eyebrow">{outcome.eyebrow}</p>
      <h1>{outcome.title}</h1>
      <p className="subtitle">{outcome.description}</p>
      <div className="outcome-payment"><div><small>Payment</small><strong>{formatCurrency(transaction.amount)} to {transaction.recipientName}</strong></div><StatusBadge status={transaction.status} /></div>
      <div className="outcome-next"><ShieldCheck size={18} /><div><strong>What to do next</strong><p>{outcome.next}</p></div></div>
      <div className="outcome-actions"><Link className="button-primary" href="/dashboard">Return to account</Link><Link className="button-secondary" href="/transactions">View activity</Link></div>
    </section>
    <p className="outcome-privacy"><LockKeyhole size={13} /> Guardian does not send money or make final decisions. A bank employee made this simulated outcome.</p>
  </div></div></AppShell>;
}
