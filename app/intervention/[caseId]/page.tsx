import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { InterventionExperience } from "@/components/intervention-experience";
import { demoStore } from "@/lib/demo-store";

export const dynamic = "force-dynamic";

export default async function InterventionPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  const caseItem = demoStore.getCase(caseId);
  if (!caseItem) notFound();
  const transaction = demoStore.getTransaction(caseItem.transactionId);
  if (!transaction) notFound();
  return <AppShell><InterventionExperience initialCase={caseItem} transaction={transaction} /></AppShell>;
}
