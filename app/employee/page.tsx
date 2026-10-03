import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { ChevronRight, ShieldCheck } from "@/components/icons";
import { StatusBadge } from "@/components/status-badge";
import { TrustRequests } from "@/components/trust-requests";
import { demoStore } from "@/lib/demo-store";
import { formatCurrency, formatDateTime } from "@/lib/format";

export const dynamic = "force-dynamic";

export default function EmployeeDashboard() {
  const { cases, transactions, recipients } = demoStore.getState();
  const trustRequests = recipients.filter((item) => item.trustStatus === "TRUST_REQUESTED");
  const openCases = cases.filter((item) => item.status !== "RESOLVED");
  return <AppShell employee><div className="page-wrap">
    <div className="employee-hero"><div><p className="eyebrow" style={{ color: "#8fc2ff" }}>Fraud operations workspace</p><h1>Scam intervention queue</h1><p className="subtitle">Review behavioral anomalies alongside customer-provided context.</p></div><div className="queue-count"><strong>{openCases.length}</strong><small>CASES NEED ATTENTION</small></div></div>
    <div className="stats-grid"><div className="card stat-card"><small>Open cases</small><strong>{openCases.length}</strong></div><div className="card stat-card"><small>High concern</small><strong>{cases.filter(c => c.assessment.assessment === "HIGH_CONCERN").length}</strong></div><div className="card stat-card"><small>Avg. risk score</small><strong>{cases.length ? Math.round(cases.reduce((a,c)=>a+c.riskAnalysis.riskScore,0)/cases.length) : 0}</strong></div><div className="card stat-card"><small>Human decisions</small><strong>{cases.filter(c=>c.status === "RESOLVED").length}</strong></div></div>
    <TrustRequests requests={trustRequests} />
    <div className="card table-card"><div className="card-header"><h2>Priority cases</h2><Link className="text-link" href="/employee/cases">View all <ChevronRight size={13} /></Link></div>
      {cases.length === 0 ? <div className="empty-state"><div className="guardian-icon"><ShieldCheck size={22} /></div><h2>No intervention cases yet</h2><p>Run the customer demo to generate Case #1042.</p><Link className="button-primary" href="/send">Start customer demo</Link></div> :
      <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Case</th><th>Customer</th><th>Payment</th><th>Risk</th><th>Recommendation</th><th>Status</th><th></th></tr></thead><tbody>{cases.map((caseItem) => { const txn=transactions.find(t=>t.id===caseItem.transactionId); return <tr key={caseItem.id}><td><strong>#{caseItem.displayId}</strong><div style={{fontSize:9,color:"#7b8596",marginTop:3}}>{formatDateTime(caseItem.createdAt)}</div></td><td>{caseItem.contextSnapshot.customer.displayName}</td><td><strong>{formatCurrency(txn?.amount??0)}</strong><div style={{fontSize:9,color:"#7b8596"}}>{txn?.recipientName}</div></td><td><strong style={{color:caseItem.riskAnalysis.riskScore>=70?"#a32f38":undefined}}>{caseItem.riskAnalysis.riskScore}</strong> / 100</td><td><StatusBadge status={caseItem.assessment.nextAction} /></td><td><StatusBadge status={caseItem.status} /></td><td><Link className="text-link" href={`/employee/cases/${caseItem.id}`}>Review →</Link></td></tr>})}</tbody></table></div>}
    </div>
  </div></AppShell>;
}
