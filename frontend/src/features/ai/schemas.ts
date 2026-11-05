import { z } from "zod";

export const QUESTION_MAX_LENGTH = 500;

const countSchema = z.number().int().nonnegative();
const technicianSchema = z.object({ userId: z.string(), name: z.string() });

const resultSchema = z.discriminatedUnion("kind", [
  z.object({
    kind: z.literal("technician_jobs"),
    technician: technicianSchema,
    total: countSchema,
    items: z.array(z.object({ orderId: z.string(), orderNo: z.string(), serviceType: z.string(), completedAt: z.string() })),
    truncated: z.boolean(),
  }),
  z.object({ kind: z.literal("top_technician"), jobsCompleted: countSchema, total: countSchema, items: z.array(technicianSchema), truncated: z.boolean() }),
  z.object({ kind: z.literal("completed_count"), total: countSchema }),
]);

export const aiAnswerSchema = z.object({
  status: z.enum(["answered", "unsupported", "clarification_required"]),
  answer: z.string(),
  summarySource: z.enum(["ai", "template"]).nullable(),
  notice: z.string().nullable(),
  period: z.object({ label: z.string(), startDate: z.string(), endDate: z.string() }).nullable(),
  result: resultSchema.nullable(),
});

export type AiAnswer = z.infer<typeof aiAnswerSchema>;
export type AiResult = z.infer<typeof resultSchema>;
