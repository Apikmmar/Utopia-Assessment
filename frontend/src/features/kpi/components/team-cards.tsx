import { Card } from "@/components/ui/card";
import { formatMyr } from "@/features/orders/money";
import type { Dashboard } from "../schemas";

// One labelled figure.
function StatCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Card className="flex flex-col gap-1 p-5 sm:p-6">
      <p className="text-sm text-muted">{label}</p>
      <p className="text-3xl font-semibold tracking-tight tabular-nums">{value}</p>
      <p className="text-xs text-muted">{hint}</p>
    </Card>
  );
}

// The team's totals for the week: jobs completed, total amount billed, and visits postponed.
export function TeamCards({ team }: { team: Dashboard["team"] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <StatCard label="Jobs completed" value={String(team.jobsCompleted)} hint="Completion records submitted this week" />
      <StatCard label="Total amount" value={formatMyr(team.totalAmount)} hint="Sum of final amounts billed" />
      <StatCard label="Postponed" value={String(team.postponed)} hint="Visits postponed this week" />
    </div>
  );
}
