import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { EmployeeActions } from "@/components/employee-actions";
import { Check, TriangleAlert } from "@/components/icons";
import { StatusBadge } from "@/components/status-badge";
import { demoStore } from "@/lib/demo-store";
import { formatCurrency, formatDateTime } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function CaseDetailPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params; const caseItem=demoStore.getCase(caseId); if(!caseItem) notFound();
  const transaction=demoStore.getTransaction(caseItem.transactionId); if(!transaction) notFound(); const customerName=caseItem.contextSnapshot.customer.displayName;
  const riskSignals=caseItem.riskAnalysis.signals.filter(s=>s.category==="RISK"); const normalSignals=caseItem.riskAnalysis.signals.filter(s=>s.category==="NORMAL");
  return <AppShell employee><div className="page-wrap">
    <div className="page-heading"><div><p className="eyebrow">Scam intervention case #{caseItem.displayId} · {caseItem.institutionId ?? "reference institution"}</p><h1>{customerName}</h1><p className="subtitle">Opened {formatDateTime(caseItem.createdAt)} · Payment remains {transaction.status.toLowerCase().replaceAll("_"," ")}</p></div><StatusBadge status={caseItem.status} /></div>
    <div className="case-detail-grid"><div className="detail-stack">
      <section className="card"><div className="card-header"><h2>Transaction & behavioral evidence</h2><strong style={{fontSize:20}}>{formatCurrency(transaction.amount)} → {transaction.recipientName}</strong></div><div className="section-body"><div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:15}}><div><p className="eyebrow">Behavioral risk score</p><strong style={{fontSize:28,color:"#b63b43"}}>{caseItem.riskAnalysis.riskScore} / 100</strong></div><StatusBadge status={caseItem.riskAnalysis.riskLevel} /></div><div className="signal-grid">{riskSignals.map(s=><div className="signal-item risk" key={s.type}><strong><TriangleAlert size={12} style={{display:"inline",marginRight:5,color:"#b86116"}} />{s.type.replaceAll("_"," ")}</strong><p>{s.explanation}</p></div>)}{normalSignals.map(s=><div className="signal-item normal" key={s.type}><strong><Check size={12} style={{display:"inline",marginRight:5,color:"#147d5a"}} />{s.type.replaceAll("_"," ")}</strong><p>{s.explanation}</p></div>)}</div></div></section>
      <section className="card"><div className="card-header"><h2>Customer interview</h2><span className="subtitle">Customer-provided statements</span></div><div className="section-body transcript">{caseItem.messages.map(m=><div className={`transcript-item ${m.role}`} key={m.id}><strong>{m.role === "agent" ? "Guardian assistant" : customerName}</strong><p>“{m.content}”</p></div>)}</div></section>
      <section className="card"><div className="card-header"><h2>Conversation evidence</h2><span className="subtitle">Distinct from behavioral risk</span></div><div className="section-body">{caseItem.assessment.socialEngineeringSignals.length?<div className="signal-chips">{caseItem.assessment.socialEngineeringSignals.map(s=><span className="signal-chip" key={s}>⚠ {s.replaceAll("_"," ")}</span>)}</div>:<p className="subtitle">No social-engineering indicators identified yet.</p>}</div></section>
    </div><aside className="detail-stack">
      <div className="card recommendation-card"><span className="recommendation-label">AI recommendation</span><h2>{caseItem.assessment.nextAction.replaceAll("_"," ")} FOR HUMAN VERIFICATION</h2><p>{caseItem.assessment.customerExplanation}</p><div className="confidence"><span>Confidence</span><strong>{Math.round(caseItem.assessment.confidence*100)}% · {caseItem.assessment.modelSource === "gemini" ? "Gemini" : "Demo fallback"}</strong></div></div>
      <EmployeeActions caseItem={caseItem} />
    </aside></div>
  </div></AppShell>;
}
