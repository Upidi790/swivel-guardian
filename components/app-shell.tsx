import Link from "next/link";
import type { ReactNode } from "react";
import { Bell, Building2, House, Send, ShieldCheck, Users, WalletCards } from "@/components/icons";
import { ResetDemoButton } from "@/components/reset-demo-button";

const nav = [
  { href: "/dashboard", label: "Overview", icon: House },
  { href: "/send", label: "Send money", icon: Send },
  { href: "/transactions", label: "Activity", icon: WalletCards },
  { href: "/recipients", label: "Recipients", icon: Users },
  { href: "/integration", label: "Integration API", icon: Building2 },
];

export function AppShell({ children, employee = false }: { children: ReactNode; employee?: boolean }) {
  return (
    <div className="app-frame">
      <header className="topbar">
        <Link href={employee ? "/employee" : "/dashboard"} className="brand">
          <span className="brand-mark"><ShieldCheck size={23} /></span>
          <span><strong>Guardian</strong><small>SWIVEL-enabled prototype</small></span>
        </Link>
        <nav className="desktop-nav" aria-label="Primary navigation">
          {(employee
            ? [
                { href: "/employee", label: "Queue", icon: House },
                { href: "/employee/cases", label: "All cases", icon: WalletCards },
              ]
            : nav
          ).map(({ href, label, icon: Icon }) => (
            <Link href={href} key={href}><Icon size={17} />{label}</Link>
          ))}
        </nav>
        <div className="topbar-actions">
          <ResetDemoButton />
          <button type="button" className="icon-button" aria-label="Notifications"><Bell size={18} /></button>
          <Link className="profile-pill" href={employee ? "/dashboard" : "/employee"}>
            <span>{employee ? "AK" : "MR"}</span>
            <div><strong>{employee ? "Alex Kim" : "Maria Rodriguez"}</strong><small>{employee ? "Fraud specialist" : "Customer"}</small></div>
          </Link>
        </div>
      </header>
      <div className="demo-ribbon"><span>LIVE PROTOTYPE</span> Fictional data · Actions are simulated · Human decisions required</div>
      <main>{children}</main>
      {!employee && (
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {nav.map(({ href, label, icon: Icon }) => <Link href={href} key={href}><Icon size={20} /><span>{label}</span></Link>)}
        </nav>
      )}
    </div>
  );
}
