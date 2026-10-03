import { z } from "zod";

export const transactionRequestSchema = z.object({
  recipientId: z.string().trim().min(1).optional(),
  recipientName: z.string().trim().min(2).max(100),
  amount: z.coerce.number().positive().max(1_000_000),
  memo: z.string().trim().max(140).optional().default(""),
});

export const messageRequestSchema = z.object({
  message: z.string().trim().min(1).max(2_000),
});

export const employeeActionSchema = z.object({
  action: z.enum(["MARK_REVIEWED", "RELEASE", "KEEP_UNDER_REVIEW", "CANCEL"]),
});
