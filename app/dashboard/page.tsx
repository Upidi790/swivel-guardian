import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { ArrowDownLeft, ArrowUpRight, ChevronRight, LockKeyhole, Plus, Send, ShieldEllipsis, WalletCards } from "@/components/icons";
import { demoStore } from "@/lib/demo-store";
import { formatCurrency, formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default function DashboardPage() {
  const { customer, transactions, recipients } = demoStore.getState();
  return (
    <AppShell>
      <div className="page-wrap">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Saturday, October 3</p>
            <h1>Good afternoon, Maria.</h1>
            <p className="subtitle">Here&apos;s what&apos;s happening with your account.</p>
          </div>
          <Link className="button-primary" href="/send"><Send size={16} /> Send money</Link>
        </div>

        <section className="dashboard-grid">
          <div className="balance-card">
            <div className="balance-label"><WalletCards size={15} /> Everyday Checking</div>
            <div className="balance-value">{formatCurrency(customer.checkingBalance)}</div>
            <div className="account-number">Available balance ···· {customer.accountLastFour}</div>
            <div className="balance-actions">
              <Link href="/send" className="solid"><Send size={15} /> Send money</Link>
              <Link href="/recipients" className="ghost"><Plus size={15} /> Add recipient</Link>
            </div>
          </div>
          <div className="card guardian-card">
            <div>
              <div className="guardian-icon"><ShieldEllipsis size={22} /></div>
              <h2>Guardian is looking out for you.</h2>
              <p>When a payment differs from your normal behavior, we pause and ask—not assume. You stay in control, with a person making any final decision.</p>
            </div>
            <div className="privacy-note"><LockKeyhole size={14} /> We never read your texts, email, or phone calls.</div>
          </div>
        </section>

        <section className="dashboard-lower">
          <div className="card">
            <div className="card-header"><h2>Recent activity</h2><Link className="text-link" href="/transactions">View all <ChevronRight size={13} /></Link></div>
            <div>
              {transactions.slice(0, 4).map((transaction) => (
                <div className="transaction-row" key={transaction.id}>
                  <div className={`transaction-icon ${transaction.direction === "incoming" ? "incoming" : ""}`}>
                    {transaction.direction === "incoming" ? <ArrowDownLeft size={17} /> : <ArrowUpRight size={17} />}
                  </div>
                  <div className="transaction-main"><strong>{transaction.recipientName}</strong><small>{transaction.memo} · {formatDate(transaction.createdAt)}</small></div>
                  <div className={`transaction-amount ${transaction.direction === "incoming" ? "incoming" : ""}`}>
                    {transaction.direction === "incoming" ? "+" : "−"}{formatCurrency(transaction.amount)}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="card-header"><h2>Trusted recipients</h2><Link className="text-link" href="/recipients">Manage</Link></div>
            <div className="recipients-strip">
              {recipients.filter((r) => r.trustStatus === "TRUSTED").map((recipient) => (
                <Link href={`/send?recipient=${recipient.id}`} className="recipient-compact" key={recipient.id}>
                  <span className="avatar">{recipient.name.split(" ").map((v) => v[0]).join("").slice(0, 2)}</span>
                  <span><strong>{recipient.name}</strong><small>{recipient.relationship} · {recipient.previousTransactionCount} past payments</small></span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
