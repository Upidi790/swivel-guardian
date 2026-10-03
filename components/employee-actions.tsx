"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Headphones, LockKeyhole } from "@/components/icons";
import type { InterventionCase } from "@/lib/types";

export function EmployeeActions({ caseItem }: { caseItem: InterventionCase }) {
  const [busy,setBusy]=useState(""); const [error,setError]=useState(""); const router=useRouter();
  async function act(action:string){setBusy(action);setError("");try{const response=await fetch(`/api/v1/cases/${caseItem.id}/human-decision`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action,decidedBy:"alex_kim_demo"})});const payload=await response.json();if(!response.ok)throw new Error(payload.error);router.refresh();}catch(e){setError(e instanceof Error?e.message:"Action failed.");}finally{setBusy("");}}
  const resolved=caseItem.status==="RESOLVED";
  return <div className="card employee-actions"><h3>Human decision</h3><p>These are simulated controls. Confirm the customer&apos;s identity and circumstances before making a decision.</p>{error&&<div className="error-box">{error}</div>}
    <button type="button" className="button-secondary" disabled={!!busy||resolved}><Headphones size={14}/> Call customer (simulated)</button>
    <button type="button" className="button-primary" onClick={()=>act("RELEASE")} disabled={!!busy||resolved}>{busy==="RELEASE"?"Applying…":"Release transaction"}</button>
    <button type="button" className="button-quiet" onClick={()=>act("KEEP_UNDER_REVIEW")} disabled={!!busy||resolved}>Keep under review</button>
    <button type="button" className="button-quiet" onClick={()=>act("MARK_REVIEWED")} disabled={!!busy||resolved}>Mark reviewed</button>
    <button type="button" className="button-danger" onClick={()=>act("CANCEL")} disabled={!!busy||resolved}>Cancel transaction — demo</button>
    <div className="human-note"><LockKeyhole size={12} style={{display:"inline",marginRight:5}}/>Guardian cannot execute these actions. Only this employee workflow can change the payment state.</div>
  </div>;
}
