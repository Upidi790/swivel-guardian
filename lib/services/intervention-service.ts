import { getGuardianService } from "@/lib/guardian";

export async function addCustomerMessage(caseId: string, content: string) {
  return getGuardianService().addMessage(caseId, content);
}
