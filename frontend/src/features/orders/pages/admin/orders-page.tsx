import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { useMe } from "@/features/auth/queries";
import { failureMessage } from "@/lib/failure-message";
import { useDebouncedCallback } from "@/lib/use-debounced-callback";
import { EmptyState, ErrorState, LoadingState } from "../../components/list-states";
import { OrderFilters } from "../../components/order-filters";
import { OrdersTable } from "../../components/orders-table";
import { readOrderFilters, toOrderFilterParams, type OrderListFilters } from "../../filters";
import { useOrders, useTechnicians } from "../../queries";

const SEARCH_DEBOUNCE_MS = 300;
const ITEM_LABEL = { one: "order", many: "orders" };

// Orders list for admins and managers, with search, status, technician, and sort kept in the URL; admins can create orders.
export function OrdersPage() {
  const isAdmin = useMe().data?.roleCode === "admin";
  const technicians = useTechnicians(isAdmin);
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = readOrderFilters(searchParams);
  const [searchDraft, setSearchDraft] = useState(filters.search);
  const [syncedSearch, setSyncedSearch] = useState(filters.search);
  if (syncedSearch !== filters.search) {
    setSyncedSearch(filters.search);
    setSearchDraft(filters.search);
  }
  const orders = useOrders(filters);

  const updateFilters = (changes: Partial<OrderListFilters>, replace = false) => {
    setSearchParams((current) => toOrderFilterParams({ ...readOrderFilters(current), ...changes }), { replace });
  };
  const writeSearch = useDebouncedCallback((value: string) => updateFilters({ search: value, page: 1 }, true), SEARCH_DEBOUNCE_MS);

  return (
    <section aria-labelledby="orders-title" className="flex flex-col gap-6">
      <PageHeader
        id="orders-title"
        title="Orders"
        description="Every service order and where it stands."
        actions={
          isAdmin ? (
            <Button asChild>
              <Link to="/orders/new">New order</Link>
            </Button>
          ) : null
        }
      />
      <OrderFilters
        search={searchDraft}
        status={filters.status[0] ?? ""}
        technicianId={filters.technicianId}
        sort={filters.sort}
        technicians={isAdmin ? (technicians.data ?? []) : undefined}
        onSearchChange={(value) => {
          setSearchDraft(value);
          writeSearch(value);
        }}
        onStatusChange={(status) => updateFilters({ status: status ? [status] : [], page: 1 })}
        onTechnicianChange={(technicianId) => updateFilters({ technicianId, page: 1 })}
        onSortChange={(sort) => updateFilters({ sort, page: 1 })}
      />
      <div aria-busy={orders.isFetching} className="flex flex-col gap-4">
        {orders.isPending ? (
          <LoadingState>Loading orders…</LoadingState>
        ) : orders.isError ? (
          <ErrorState message={failureMessage(orders.error, "We could not load orders. Try again.")} onRetry={() => void orders.refetch()} />
        ) : orders.data.items.length === 0 ? (
          <EmptyState>{filters.search || filters.status.length || filters.technicianId ? "No orders match your filters." : "No orders yet."}</EmptyState>
        ) : (
          <>
            <OrdersTable orders={orders.data.items} />
            <Pagination
              page={orders.data.page}
              pageSize={orders.data.pageSize}
              total={orders.data.total}
              itemLabel={ITEM_LABEL}
              onPageChange={(page) => updateFilters({ page })}
            />
          </>
        )}
      </div>
    </section>
  );
}
