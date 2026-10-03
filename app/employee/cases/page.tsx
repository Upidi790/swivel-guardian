import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { StatusBadge } from "@/components/status-badge";
import { demoStore } from "@/lib/demo-store";
import { formatCurrency, formatDateTime } from "@/lib/format";

export const dynamic = "force-dynamic";

export default function CasesPage() {
  const { cases, transactions } = demoStore.getState();
  return <AppShell employee><div className="page-wrap"><div className="page-heading"><div><p className="eyebrow">Fraud operations</p><h1>Intervention cases</h1><p className="subtitle">AI recommendations are advisory. Employees make all final payment decisions.</p></div></div>
    <div className="card table-card">{cases.length===0?<div className="empty-state"><h2>No cases found</h2><p>Complete the unusual payment flow to create a review case.</p><Link className="button-primary" href="/send">Start demo</Link></div>:<div style={{overflowX:"auto"}}><table className="data-table"><thead><tr><th>Case</th><th>Customer</th><th>Transaction</th><th>Behavioral risk</th><th>Conversation assessment</th><th>Status</th><th></th></tr></thead><tbody>{cases.map(c=>{const t=transactions.find(x=>x.id===c.transactionId);return <tr key={c.id}><td><strong>#{c.displayId}</strong><div style={{fontSize:9,color:"#7b8596"}}>{formatDateTime(c.createdAt)}</div></td><td>{c.contextSnapshot.customer.displayName}</td><td>{formatCurrency(t?.amount??0)} → {t?.recipientName}</td><td>{c.riskAnalysis.riskScore} / 100</td><td><StatusBadge status={c.assessment.assessment} /></td><td><StatusBadge status={c.status} /></td><td><Link className="text-link" href={`/employee/cases/${c.id}`}>Open →</Link></td></tr>})}</tbody></table></div>}</div>
  </div></AppShell>;
}
