import type { DemoState } from "@/lib/types";

const DAY_MS = 86_400_000;

export function createSeedState(): DemoState {
  // Derived from the real clock so the demo keeps its "added minutes ago" and
  // "recent activity" framing on any day it is run.
  const now = Date.now();
  const isoDaysAgo = (days: number) => new Date(now - days * DAY_MS).toISOString();
  const isoMinutesAgo = (minutes: number) => new Date(now - minutes * 60_000).toISOString();
  return {
    customer: {
      id: "maria_001",
      name: "Maria Rodriguez",
      initials: "MR",
      location: "San Antonio, TX",
      checkingBalance: 8432.18,
      accountLastFour: "4821",
      knownDeviceId: "iphone_maria",
      knownRegion: "san_antonio",
      medianTransfer: 120,
      p95Transfer: 430,
    },
    recipients: [
      {
        id: "recipient_elena",
        name: "Elena Rodriguez",
        relationship: "Daughter",
        createdAt: isoDaysAgo(600),
        previousTransactionCount: 18,
        trustStatus: "TRUSTED",
      },
      {
        id: "recipient_cps",
        name: "CPS Energy",
        relationship: "Utility",
        createdAt: isoDaysAgo(900),
        previousTransactionCount: 24,
        trustStatus: "TRUSTED",
      },
      {
        id: "recipient_secure",
        name: "Secure Asset Services",
        relationship: "New recipient",
        createdAt: isoMinutesAgo(2),
        previousTransactionCount: 0,
        trustStatus: "UNVERIFIED",
      },
    ],
    transactions: [
      {
        id: "txn_0998",
        userId: "maria_001",
        recipientId: "recipient_heb",
        recipientName: "H-E-B Grocery",
        amount: 86.42,
        memo: "Groceries",
        deviceId: "iphone_maria",
        ipRegion: "san_antonio",
        createdAt: isoDaysAgo(1),
        status: "COMPLETED",
        direction: "outgoing",
      },
      {
        id: "txn_0997",
        userId: "maria_001",
        recipientId: "recipient_elena",
        recipientName: "Elena Rodriguez",
        amount: 120,
        memo: "Dinner",
        deviceId: "iphone_maria",
        ipRegion: "san_antonio",
        createdAt: isoDaysAgo(3),
        status: "COMPLETED",
        direction: "outgoing",
      },
      {
        id: "txn_0996",
        userId: "maria_001",
        recipientId: "employer",
        recipientName: "Alamo Health Partners",
        amount: 2450.31,
        memo: "Direct deposit",
        deviceId: "system",
        ipRegion: "san_antonio",
        createdAt: isoDaysAgo(5),
        status: "COMPLETED",
        direction: "incoming",
      },
      {
        id: "txn_0995",
        userId: "maria_001",
        recipientId: "recipient_cps",
        recipientName: "CPS Energy",
        amount: 146.87,
        memo: "Monthly utility",
        deviceId: "iphone_maria",
        ipRegion: "san_antonio",
        createdAt: isoDaysAgo(8),
        status: "COMPLETED",
        direction: "outgoing",
      },
    ],
    cases: [],
  };
}
