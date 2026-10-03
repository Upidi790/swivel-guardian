import { AppShell } from "@/components/app-shell";
import { Search } from "@/components/icons";
import { StatusBadge } from "@/components/status-badge";
import { demoStore } from "@/lib/demo-store";
import { formatCurrency, formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default function TransactionsPage() {
  const { transactions } = demoStore.getState();
  return (
    <AppShell>
      <div className="page-wrap">
        <div className="page-heading"><div><p className="eyebrow">Account activity</p><h1>Transactions</h1><p className="subtitle">Everyday Checking · All account activity</p></div></div>
        <div className="card table-card">
          <div className="table-toolbar"><div className="search-box"><Search size={14} /><input aria-label="Search transactions" placeholder="Search transactions" /></div><span className="subtitle">{transactions.length} transactions</span></div>
          <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Transaction</th><th>Amount</th><th>Date</th><th>Memo</th><th>Status</th></tr></thead><tbody>
            {transactions.map((transaction) => <tr key={transaction.id}>
              <td><strong>{transaction.recipientName}</strong><div style={{ color: "#7b8596", fontSize: 9, marginTop: 3 }}>{transaction.id}</div></td>
              <td style={{ color: transaction.direction === "incoming" ? "#147d5a" : undefined, fontWeight: 750 }}>{transaction.direction === "incoming" ? "+" : "−"}{formatCurrency(transaction.amount)}</td>
              <td>{formatDate(transaction.createdAt)}</td><td>{transaction.memo || "—"}</td><td><StatusBadge status={transaction.status} /></td>
            </tr>)}
          </tbody></table></div>
        </div>
      </div>
    </AppShell>
  );
}
