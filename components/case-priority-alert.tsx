import Link from "next/link";
import { Bell, ShieldEllipsis } from "@/components/icons";
import type { InterventionCase, Transaction } from "@/lib/types";

function fallbackMessage(caseItem: InterventionCase, transaction?: Transaction) {
  const signals = caseItem.assessment.socialEngineeringSignals.map((item) => item.replaceAll("_", " ").toLowerCase());
  const evidence = signals.length ? signals.slice(0, 2).join(" and ") : "high-risk social-engineering indicators";
  return `Guardian identified ${evidence} for ${transaction?.recipientName ?? "this payment"}. The payment is held and has not been sent; please review the full case summary within five minutes.`;
}

export function CasePriorityAlert({ caseItem, transaction }: { caseItem: InterventionCase; transaction?: Transaction }) {
  if (caseItem.status !== "ESCALATED" || caseItem.assessment.assessment !== "HIGH_CONCERN") return null;
  return <aside className="case-priority-alert" role="status" aria-live="polite"><div className="priority-alert-icon"><Bell size={18} /></div><div><p className="priority-alert-label">New high-priority Guardian case</p><h2>Immediate specialist review requested</h2><p>{caseItem.assessment.employeeNotification ?? fallbackMessage(caseItem, transaction)}</p><Link href={`/employee/cases/${caseItem.id}`} className="button-primary"><ShieldEllipsis size={15} /> Review full case summary</Link></div></aside>;
}
