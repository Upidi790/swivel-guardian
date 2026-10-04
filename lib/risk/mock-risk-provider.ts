import type { RiskContext, RiskProvider } from "@/lib/risk/provider";
import type { RiskAnalysis, RiskSignal, Transaction } from "@/lib/types";

export class MockRiskProvider implements RiskProvider {
  async analyzeTransaction(transaction: Transaction, context: RiskContext): Promise<RiskAnalysis> {
    const { customer, recipient } = context;
    const previousCount = recipient.previousTransactionCount;
    const recipientAgeMs = Date.now() - new Date(recipient.createdAt).getTime();
    const recentlyAdded = recipientAgeMs < 24 * 60 * 60 * 1000;
    const newRecipient = previousCount === 0;
    const amountRatio = transaction.amount / customer.p95Transfer;
    const knownDevice = customer.knownDeviceIds.includes(transaction.deviceId);
    const normalRegion = customer.knownRegions.includes(transaction.ipRegion);

    let score = 8;
    const signals: RiskSignal[] = [];

    if (newRecipient) {
      score += 26;
      signals.push({
        type: "NEW_RECIPIENT",
        severity: 1,
        explanation: "No previous transfers exist for this recipient.",
        category: "RISK",
      });
    }
    if (transaction.amount > customer.p95Transfer) {
      const severity = Math.min(1, amountRatio / 4.65);
      score += Math.round(34 * severity);
      signals.push({
        type: "AMOUNT_ANOMALY",
        severity,
        explanation: `${transaction.amount.toLocaleString("en-US", { style: "currency", currency: "USD" })} is well above this customer's ${customer.p95Transfer.toLocaleString("en-US", { style: "currency", currency: "USD" })} normal 95th-percentile transfer.`,
        category: "RISK",
      });
    }
    if (recentlyAdded) {
      score += 14;
      signals.push({
        type: "RECIPIENT_RECENTLY_ADDED",
        severity: 0.92,
        explanation: "This recipient was added only minutes ago.",
        category: "RISK",
      });
    }
    if (!knownDevice) {
      score += 15;
      signals.push({
        type: "UNKNOWN_DEVICE",
        severity: 0.8,
        explanation: "The device is not one the customer normally uses.",
        category: "RISK",
      });
    } else {
      signals.push({
        type: "KNOWN_DEVICE",
        severity: 0,
        explanation: "The payment was initiated from a recognized customer device.",
        category: "NORMAL",
      });
    }
    if (!normalRegion) {
      score += 12;
      signals.push({
        type: "LOCATION_DEVIATION",
        severity: 0.75,
        explanation: "The payment originated outside the customer's normal region.",
        category: "RISK",
      });
    } else {
      signals.push({
        type: "NORMAL_REGION",
        severity: 0,
        explanation: "The payment originated in the customer's normal region.",
        category: "NORMAL",
      });
    }

    // Verified trust lowers recipient-identity concern, but it is deliberately
    // not a bypass: an amount far outside the customer's range re-applies the
    // full score, so a trusted payee cannot be used to walk a large payment
    // past the intervention.
    if (recipient.trustStatus === "TRUSTED") {
      const extremeAmount = transaction.amount > customer.p95Transfer * 3;
      signals.push({
        type: "TRUSTED_RECIPIENT",
        severity: 0,
        explanation: extremeAmount
          ? "This recipient is verified, but the amount is far outside the customer's normal range, so trust does not reduce the score."
          : "This recipient was previously verified by the customer and an employee.",
        category: "NORMAL",
      });
      if (!extremeAmount) score -= 10;
    }

    // No per-scenario overrides: the signature $2,000 demo reaches 82/100 from
    // these weights alone (8 base + 26 new recipient + 34 amount + 14 recency).
    score = Math.max(0, Math.min(100, score));

    return {
      transactionId: transaction.id,
      riskScore: score,
      riskLevel: score >= 70 ? "HIGH" : score >= 40 ? "MEDIUM" : "LOW",
      // $100 is the customer-convenience floor. A new $20 payee should not
      // create a frustrating intervention on its own.
      requiresIntervention: transaction.amount >= 100 && score >= 40,
      signals,
      baseline: {
        medianTransfer: customer.normalTransferMedian,
        p95Transfer: customer.p95Transfer,
        previousRecipientTransactions: previousCount,
      },
      provider: "mock",
    };
  }
}
