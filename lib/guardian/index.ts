import { createDemoProviders } from "@/lib/guardian/demo-adapters";
import { GuardianService } from "@/lib/guardian/service";

const globalGuardian = globalThis as unknown as { guardianService?: GuardianService };

export function getGuardianService() {
  globalGuardian.guardianService ??= new GuardianService(createDemoProviders());
  return globalGuardian.guardianService;
}

export * from "@/lib/guardian/contracts";
export * from "@/lib/guardian/providers";
