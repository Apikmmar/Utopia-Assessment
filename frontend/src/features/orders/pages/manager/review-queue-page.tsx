import { PageHeader } from "@/components/ui/page-header";
import { failureMessage } from "@/lib/failure-message";
import { EmptyState, ErrorState, LoadingState } from "../../components/list-states";
import { OrdersTable } from "../../components/orders-table";
import type { OrderListFilters } from "../../filters";
import { useOrders } from "../../queries";

const REVIEW_FILTERS: OrderListFilters = { search: "", status: ["job_done"], technicianId: "", sort: "oldest", page: 1, pageSize: 100 };

// Manager queue of finished jobs waiting for review, oldest first.
export function ReviewQueuePage() {
  const orders = useOrders(REVIEW_FILTERS, { refetchOnWindowFocus: true });
  return (
    <section aria-labelledby="review-title" className="flex flex-col gap-6">
      <PageHeader id="review-title" title="Review" description="Finished jobs waiting for your review, oldest first." />
      {orders.isPending ? (
        <LoadingState>Loading jobs…</LoadingState>
      ) : orders.isError ? (
        <ErrorState message={failureMessage(orders.error, "We could not load jobs to review. Try again.")} onRetry={() => void orders.refetch()} />
      ) : orders.data.items.length === 0 ? (
        <EmptyState>No finished jobs are waiting for review.</EmptyState>
      ) : (
        <OrdersTable orders={orders.data.items} />
      )}
    </section>
  );
}
