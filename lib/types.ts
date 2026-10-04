export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";
export type TransactionStatus =
  | "PENDING_INTERVENTION"
  | "COMPLETED"
  | "UNDER_REVIEW"
  | "RELEASED"
  | "CANCELLED";
export type CaseStatus = "OPEN" | "ESCALATED" | "REVIEWED" | "RESOLVED";
export type AssessmentLevel = "LOW_CONCERN" | "NEEDS_CLARIFICATION" | "HIGH_CONCERN";
export type NextAction = "ASK_FOLLOW_UP" | "ALLOW" | "REVIEW" | "ESCALATE";

export interface Customer {
  id: string;
  name: string;
  initials: string;
  location: string;
  checkingBalance: number;
  accountLastFour: string;
  knownDeviceId: string;
  knownRegion: string;
  medianTransfer: number;
  p95Transfer: number;
}

export interface Recipient {
  id: string;
  name: string;
  relationship: string;
  createdAt: string;
  previousTransactionCount: number;
  trustStatus: "TRUSTED" | "UNVERIFIED" | "TRUST_REQUESTED";
}

export interface TransactionInput {
  userId: string;
  recipientId?: string;
  recipientName: string;
  amount: number;
  memo?: string;
  deviceId: string;
  ipRegion: string;
}

export interface Transaction extends TransactionInput {
  id: string;
  createdAt: string;
  status: TransactionStatus;
  direction: "outgoing" | "incoming";
  institutionId?: string;
  rail?: import("@/lib/guardian/contracts").TransactionIntent["rail"];
  currency?: string;
  channel?: import("@/lib/guardian/contracts").TransactionIntent["channel"];
  destinationType?: import("@/lib/guardian/contracts").TransactionIntent["destination"]["type"];
}

export interface RiskSignal {
  type: string;
  severity: number;
  explanation: string;
  category: "RISK" | "NORMAL";
}

export interface RiskAnalysis {
  transactionId: string;
  riskScore: number;
  riskLevel: RiskLevel;
  requiresIntervention: boolean;
  signals: RiskSignal[];
  baseline: {
    medianTransfer: number;
    p95Transfer: number;
    previousRecipientTransactions: number;
  };
  provider: "mock" | "remote" | "remote-fallback";
}

export interface ChatMessage {
  id: string;
  role: "agent" | "customer";
  content: string;
  createdAt: string;
}

export interface AgentAssessment {
  assessment: AssessmentLevel;
  confidence: number;
  socialEngineeringSignals: string[];
  nextAction: NextAction;
  customerExplanation: string;
  nextQuestion: string | null;
  rationale: string[];
  employeeNotification?: string;
  modelSource: "gemini" | "deterministic-fallback";
}

export interface InterventionCase {
  id: string;
  displayId: string;
  customerId: string;
  institutionId?: string;
  transactionId: string;
  status: CaseStatus;
  createdAt: string;
  updatedAt: string;
  riskAnalysis: RiskAnalysis;
  messages: ChatMessage[];
  assessment: AgentAssessment;
  employeeNotes: string[];
  supportRequest?: "LIVE_CHAT" | "PHONE_CALL";
  supportStatus?: "UNREQUESTED" | "QUEUED" | "CALL_REQUESTED" | "ASSIGNED";
  resolution?: "RELEASED" | "UNDER_REVIEW" | "CANCELLED";
  contextSnapshot: {
    customer: import("@/lib/guardian/contracts").CustomerContext;
    recipient: import("@/lib/guardian/contracts").RecipientContext;
  };
}

export interface DemoState {
  customer: Customer;
  recipients: Recipient[];
  transactions: Transaction[];
  cases: InterventionCase[];
}
