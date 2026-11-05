import { apiRequest } from "@/lib/api-client";
import { dashboardSchema, type Dashboard } from "./schemas";

// Fetches team totals and the leaderboard for the week containing the date, or this week when there is none.
export async function getDashboard(date: string | undefined, signal?: AbortSignal): Promise<Dashboard> {
  return dashboardSchema.parse(await apiRequest("/kpi/dashboard", { query: { date }, signal }));
}
