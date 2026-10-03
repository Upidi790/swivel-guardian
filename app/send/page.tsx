import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { PaymentForm } from "@/components/payment-form";
import { LockKeyhole, ShieldCheck, UserRound } from "@/components/icons";
import { demoStore } from "@/lib/demo-store";

export const dynamic = "force-dynamic";

export default function SendPage() {
  const { recipients, customer } = demoStore.getState();
  return (
    <AppShell>
      <div className="page-wrap">
        <div className="page-heading"><div><p className="eyebrow">Payments</p><h1>Send money</h1><p className="subtitle">Transfer securely from Everyday Checking ···· {customer.accountLastFour}</p></div></div>
        <div className="form-layout">
          <div className="card payment-form">
            <Suspense fallback={<p>Loading payment form…</p>}>
              <PaymentForm
                recipients={recipients}
                customer={{ id: customer.id, deviceId: customer.knownDeviceId, region: customer.knownRegion }}
              />
            </Suspense>
          </div>
          <aside className="card info-panel">
            <h3>How Guardian protects payments</h3>
            <div className="info-item"><ShieldCheck size={17} /><div><strong>Behavior, not surveillance</strong><p>We compare this payment with your normal account activity.</p></div></div>
            <div className="info-item"><UserRound size={17} /><div><strong>You provide the context</strong><p>If something looks unusual, we ask you directly why.</p></div></div>
            <div className="info-item"><LockKeyhole size={17} /><div><strong>People make final decisions</strong><p>Guardian can recommend review, but cannot permanently block your money.</p></div></div>
          </aside>
        </div>
      </div>
    </AppShell>
  );
}
