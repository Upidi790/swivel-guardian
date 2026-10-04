"use client";

import { useEffect, useState } from "react";
import { Check, LockKeyhole, MessageCircle, ShieldEllipsis, TriangleAlert } from "@/components/icons";
import { SupportOptions } from "@/components/support-options";
import type { InterventionCase } from "@/lib/types";

const stages = [
  { label: "Guardian activated", detail: "Reviewing payment and conversation evidence", icon: ShieldEllipsis },
  { label: "Risk investigation", detail: "Checking for social-engineering warning signs", icon: TriangleAlert },
  { label: "High-risk pattern detected", detail: "Escalating for immediate specialist support", icon: TriangleAlert },
  { label: "Payment protected", detail: "Funds are held and have not been sent", icon: LockKeyhole },
];

export function ProtectionSequence({ caseItem }: { caseItem: InterventionCase }) {
  const [stage, setStage] = useState(0);
  const [finished, setFinished] = useState(false);
  useEffect(() => {
    const timers = [
      window.setTimeout(() => setStage(1), 650),
      window.setTimeout(() => setStage(2), 1_350),
      window.setTimeout(() => setStage(3), 2_050),
      window.setTimeout(() => setFinished(true), 2_900),
    ];
    return () => timers.forEach(window.clearTimeout);
  }, []);

  if (finished) return <SupportOptions initialCase={caseItem} />;
  return <section className="protection-sequence" aria-live="polite"><div className="guardian-alert-visual" aria-hidden="true"><i className="signal-dot dot-one" /><i className="signal-dot dot-two" /><i className="signal-dot dot-three" /><span className="floating-lock"><LockKeyhole size={15} /></span><span className="floating-message"><MessageCircle size={15} /></span><div className="alert-device"><div className="alert-screen"><ShieldEllipsis size={42} /><strong>GUARDIAN</strong><small>PAYMENT PROTECTED</small></div><div className="device-base" /></div></div><div className="sequence-heading"><div className="sequence-orb"><ShieldEllipsis size={29} /></div><div><p className="eyebrow">Guardian protection sequence</p><h2>Protecting this payment</h2><p>We&apos;re pausing the payment while Guardian prepares the safest next step.</p></div></div><ol>{stages.map((item, index) => { const Icon = item.icon; const active = index === stage; const complete = index < stage; return <li className={active ? "active" : complete ? "complete" : ""} key={item.label}><span>{complete ? <Check size={14} /> : <Icon size={14} />}</span><div><strong>{item.label}</strong><small>{item.detail}</small></div></li>; })}</ol></section>;
}
