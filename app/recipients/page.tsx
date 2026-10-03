import { AppShell } from "@/components/app-shell";
import { LockKeyhole, Plus } from "@/components/icons";
import { RecipientCards } from "@/components/recipient-cards";
import { demoStore } from "@/lib/demo-store";

export const dynamic = "force-dynamic";

export default function RecipientsPage() {
  const { recipients } = demoStore.getState();
  return (
    <AppShell>
      <div className="page-wrap">
        <div className="page-heading"><div><p className="eyebrow">Payments</p><h1>Recipients</h1><p className="subtitle">Manage the people and organizations you pay.</p></div><button type="button" className="button-primary"><Plus size={15} /> Add recipient</button></div>
        <div className="trust-callout"><LockKeyhole size={18} style={{ flex: "none" }} /><div><strong style={{ display: "block" }}>Trusted status never bypasses unusual-payment checks.</strong>New trust requests require additional verification and employee approval. Dramatically unusual amounts may still trigger an intervention.</div></div>
        <RecipientCards initialRecipients={recipients} />
      </div>
    </AppShell>
  );
}
