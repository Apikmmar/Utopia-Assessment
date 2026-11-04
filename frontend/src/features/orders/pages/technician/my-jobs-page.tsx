import { PageHeader } from "@/components/ui/page-header";
import { failureMessage } from "@/lib/failure-message";
import { JobCard } from "../../components/job-card";
import { EmptyState, ErrorState, LoadingState } from "../../components/list-states";
import type { OrderListFilters } from "../../filters";
import { useOrders } from "../../queries";
import { ACTIVE_JOB_STATUSES, FINISHED_JOB_STATUSES } from "../../statuses";

const ACTIVE_FILTERS: OrderListFilters = { search: "", status: ACTIVE_JOB_STATUSES, technicianId: "", sort: "oldest", page: 1, pageSize: 100 };
const RECENT_FILTERS: OrderListFilters = { search: "", status: FINISHED_JOB_STATUSES, technicianId: "", sort: "newest", page: 1, pageSize: 10 };

// Technician's jobs in one column: active jobs first, oldest first, then the most recent finished ones; refreshed on focus.
export function MyJobsPage() {
  const active = useOrders(ACTIVE_FILTERS, { refetchOnWindowFocus: true });
  const recent = useOrders(RECENT_FILTERS, { refetchOnWindowFocus: true });
  return (
    <section aria-labelledby="jobs-title" className="mx-auto flex w-full max-w-xl flex-col gap-6">
      <PageHeader id="jobs-title" title="My jobs" description="Tap a job to see the details and update it." />
      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-muted">Active</h2>
        {active.isPending ? (
          <LoadingState>Loading your jobs…</LoadingState>
        ) : active.isError ? (
          <ErrorState message={failureMessage(active.error, "We could not load your jobs. Try again.")} onRetry={() => void active.refetch()} />
        ) : active.data.items.length === 0 ? (
          <EmptyState>No active jobs right now.</EmptyState>
        ) : (
          <ul aria-label="Active jobs" className="flex flex-col gap-3">
            {active.data.items.map((job) => (
              <JobCard key={job.orderId} job={job} />
            ))}
          </ul>
        )}
      </div>
      {recent.data && recent.data.items.length > 0 ? (
        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-muted">Recently finished</h2>
          <ul aria-label="Recently finished jobs" className="flex flex-col gap-3">
            {recent.data.items.map((job) => (
              <JobCard key={job.orderId} job={job} />
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
