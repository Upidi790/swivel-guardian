import { AppShell } from "@/components/app-shell";
import { IntegrationInspector } from "@/components/integration-inspector";
import { Building2, Check, ShieldCheck } from "@/components/icons";

const endpoints = [
  ["POST", "/api/v1/transactions/evaluate", "Evaluate any institution's transaction intent"],
  ["POST", "/api/v1/cases/{caseId}/messages", "Continue the adaptive customer interview"],
  ["GET", "/api/v1/cases/{caseId}/summary", "Retrieve evidence and recommendation"],
  ["POST", "/api/v1/cases/{caseId}/human-decision", "Record the institution's final decision"],
];

export default function IntegrationPage() {
  return (
    <AppShell>
      <div className="page-wrap integration-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Guardian platform</p>
            <h1>One agent. Any banking experience.</h1>
            <p className="subtitle">
              The Maria application is a reference client. Guardian itself is a headless, institution-neutral intervention API.
            </p>
          </div>
          <span className="integration-version">CONTRACT v1.0</span>
        </div>

        <section className="integration-architecture card">
          <div className="architecture-node"><Building2 size={20} /><strong>Any bank app</strong><small>Web · Mobile · Branch · IVR</small></div>
          <span className="architecture-arrow">→</span>
          <div className="architecture-node accent"><ShieldCheck size={20} /><strong>Guardian API</strong><small>Assess · Interview · Explain</small></div>
          <span className="architecture-arrow">→</span>
          <div className="architecture-node"><strong>SWIVEL workflow</strong><small>Continue · Review · Human decision</small></div>
        </section>

        <section className="integration-grid">
          <div className="card endpoint-card">
            <div className="card-header"><h2>Public integration surface</h2><span className="status-badge positive">Headless</span></div>
            <div className="endpoint-list">
              {endpoints.map(([method, path, detail]) => (
                <div className="endpoint-row" key={path}>
                  <span>{method}</span><code>{path}</code><p>{detail}</p>
                </div>
              ))}
            </div>
            <div className="adapter-list">
              {[
                "CustomerContextProvider",
                "RecipientContextProvider",
                "RiskProvider",
                "TransactionRepository",
                "CaseRepository",
                "DecisionNotifier",
              ].map((adapter) => <span key={adapter}><Check size={12} /> {adapter}</span>)}
            </div>
          </div>
          <div className="card boundary-card">
            <p className="eyebrow">Integration boundary</p>
            <h2>The bank keeps control.</h2>
            <p>Guardian receives a normalized transaction intent and returns an advisory action. It never needs the institution&apos;s dashboard code and never executes the payment.</p>
            <ul>
              <li>Institution and transaction IDs remain external</li>
              <li>ACH, card, wire, RTP, P2P, and loan-payment rails</li>
              <li>Optional bank-supplied risk analysis</li>
              <li>Outbound human-decision webhook adapter</li>
            </ul>
          </div>
        </section>

        <IntegrationInspector />
      </div>
    </AppShell>
  );
}
