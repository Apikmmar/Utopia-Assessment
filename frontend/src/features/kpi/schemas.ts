import { z } from "zod";

const amountSchema = z.string().regex(/^\d+\.\d{2}$/);
const countSchema = z.number().int().nonnegative();

export const dashboardSchema = z.object({
  week: z.object({ label: z.string(), startDate: z.string(), endDate: z.string(), isCurrent: z.boolean() }),
  team: z.object({ jobsCompleted: countSchema, totalAmount: amountSchema, postponed: countSchema }),
  leaderboard: z.array(
    z.object({
      rank: z.number().int().positive(),
      technician: z.object({ userId: z.string(), name: z.string() }),
      jobsCompleted: countSchema,
      totalAmount: amountSchema,
      postponed: countSchema,
    }),
  ),
});

export type Dashboard = z.infer<typeof dashboardSchema>;
export type LeaderboardRow = Dashboard["leaderboard"][number];
