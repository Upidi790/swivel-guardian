import { MockRiskProvider } from "@/lib/risk/mock-risk-provider";
import type { RiskContext, RiskProvider } from "@/lib/risk/provider";
import { RemoteRiskProvider } from "@/lib/risk/remote-risk-provider";
import type { RiskAnalysis, Transaction } from "@/lib/types";

class FallbackRiskProvider implements RiskProvider {
  constructor(
    private readonly remote: RiskProvider,
    private readonly fallback: RiskProvider,
  ) {}

  async analyzeTransaction(transaction: Transaction, context: RiskContext): Promise<RiskAnalysis> {
    try {
      return await this.remote.analyzeTransaction(transaction, context);
    } catch (error) {
      console.warn("[SWIVEL Guardian] Remote risk provider failed; using declared mock fallback.", error);
      const result = await this.fallback.analyzeTransaction(transaction, context);
      return { ...result, provider: "remote-fallback" };
    }
  }
}

export function getRiskProvider(): RiskProvider {
  const mock = new MockRiskProvider();
  if (process.env.RISK_PROVIDER !== "remote") return mock;
  if (!process.env.RISK_ENGINE_URL) {
    console.warn("[SWIVEL Guardian] RISK_PROVIDER=remote but RISK_ENGINE_URL is missing; using mock provider.");
    return mock;
  }
  const remote = new RemoteRiskProvider(
    process.env.RISK_ENGINE_URL,
    Number(process.env.RISK_ENGINE_TIMEOUT_MS ?? 3_000),
  );
  return process.env.RISK_FALLBACK_TO_MOCK === "false" ? remote : new FallbackRiskProvider(remote, mock);
}

export type { RiskProvider } from "@/lib/risk/provider";
