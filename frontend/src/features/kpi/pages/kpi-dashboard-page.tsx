import { Navigate, useSearchParams } from "react-router";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/features/orders/components/list-states";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";
import { JobsBarChart } from "../components/bar-chart";
import { Leaderboard } from "../components/leaderboard";
import { TeamCards } from "../components/team-cards";
import { WeekPicker } from "../components/week-picker";
import { useDashboard } from "../queries";
import { readWeekDate } from "../week";

// Weekly technician performance for admins and managers: team cards, the leaderboard, and a jobs chart, with the week
// kept in the URL. A week the server refuses falls back to this week.
export function KpiDashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const date = readWeekDate(searchParams);
  const dashboard = useDashboard(date);

  if (dashboard.error instanceof ApiError && dashboard.error.code === "INVALID_PERIOD") return <Navigate to="/kpi" replace />;
  const data = dashboard.data;
  const noWork = data ? data.team.jobsCompleted === 0 && data.team.postponed === 0 : false;

  return (
    <section aria-labelledby="kpi-title" className="flex flex-col gap-6">
      <PageHeader
        id="kpi-title"
        title="Performance"
        description="Technician figures per week, Monday to Sunday, Malaysia time. Operational indicators, not payroll."
      />
      {data ? <WeekPicker week={data.week} onChange={(next) => setSearchParams(next ? { date: next } : {})} /> : null}
      {dashboard.isPending ? <LoadingState>Loading performance…</LoadingState> : null}
      {dashboard.isError && !data ? (
        <ErrorState message={failureMessage(dashboard.error, "We could not load the dashboard. Try again.")} onRetry={() => void dashboard.refetch()} />
      ) : null}
      {data ? (
        <>
          <TeamCards team={data.team} />
          {noWork ? <p className="text-sm text-muted">No jobs were completed or postponed this week.</p> : null}
          {data.leaderboard.length === 0 ? (
            <p className="text-sm text-muted">There are no technicians yet.</p>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                <h2 className="text-base font-semibold">Leaderboard</h2>
                <Leaderboard rows={data.leaderboard} />
              </div>
              <Card className="p-5 sm:p-6">
                <JobsBarChart rows={data.leaderboard} />
              </Card>
            </>
          )}
        </>
      ) : null}
    </section>
  );
}
