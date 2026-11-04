import { useState } from "react";
import { useSearchParams } from "react-router";
import { Button } from "@/components/ui/button";
import { Field, fieldAria } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { useMe } from "@/features/auth/queries";
import { cn } from "@/lib/cn";
import { failureMessage } from "@/lib/failure-message";
import { useDebouncedCallback } from "@/lib/use-debounced-callback";
import { NotificationItem } from "../components/notification-list";
import {
  NOTIFICATION_TABS,
  NOTIFICATION_TYPE_LABELS,
  NOTIFICATION_TYPES,
  PAGE_SIZE,
  readNotificationFilters,
  SEARCH_MAX_LENGTH,
  toNotificationFilterParams,
  type NotificationPageFilters,
  type NotificationTab,
} from "../notifications";
import { useNotifications } from "../queries";

const SEARCH_DEBOUNCE_MS = 300;
const TAB_LABELS: Record<NotificationTab, string> = { pending: "Pending", sent: "Sent" };
const EMPTY_MESSAGES: Record<NotificationTab, string> = {
  pending: "Nothing waiting to be sent.",
  sent: "No messages have been opened in WhatsApp yet.",
};
const ITEM_LABEL = { one: "message", many: "messages" };

// WhatsApp notifications across orders with Pending and Sent tabs, search, and a type filter, all kept in the URL.
// Admins and technicians send from here; managers see the same list without send buttons.
export function NotificationsPage() {
  const roleCode = useMe().data?.roleCode ?? "";
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = readNotificationFilters(searchParams);
  const [searchDraft, setSearchDraft] = useState(filters.search);
  const [syncedSearch, setSyncedSearch] = useState(filters.search);
  if (syncedSearch !== filters.search) {
    setSyncedSearch(filters.search);
    setSearchDraft(filters.search);
  }
  const notifications = useNotifications({
    state: filters.tab,
    search: filters.search,
    notificationType: filters.notificationType || undefined,
    page: filters.page,
    pageSize: PAGE_SIZE,
  });

  const updateFilters = (changes: Partial<NotificationPageFilters>, replace = false) => {
    setSearchParams((current) => toNotificationFilterParams({ ...readNotificationFilters(current), ...changes }), { replace });
  };
  const writeSearch = useDebouncedCallback((value: string) => updateFilters({ search: value, page: 1 }, true), SEARCH_DEBOUNCE_MS);

  return (
    <section aria-labelledby="notifications-title" className="flex flex-col gap-6">
      <PageHeader
        id="notifications-title"
        title="Notifications"
        description={
          roleCode === "manager"
            ? "WhatsApp messages across all orders."
            : "WhatsApp messages waiting to be sent, and the ones already opened."
        }
      />
      <div role="tablist" aria-label="Message state" className="flex w-full gap-1 rounded-lg bg-subtle p-1 sm:w-auto sm:self-start">
        {NOTIFICATION_TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={filters.tab === tab}
            onClick={() => updateFilters({ tab, page: 1 })}
            className={cn(
              "min-h-9 flex-1 rounded-md px-4 text-sm font-medium transition-colors sm:flex-none",
              filters.tab === tab ? "bg-card text-foreground shadow-xs" : "text-muted hover:text-foreground",
            )}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>
      {filters.tab === "sent" ? (
        <p className="text-sm text-muted">Sent means the message was opened in WhatsApp. The app cannot confirm it was delivered.</p>
      ) : null}
      <form role="search" onSubmit={(event) => event.preventDefault()} className="grid gap-3 sm:grid-cols-[1fr_12rem]">
        <Field id="notification-search" label="Search by order number or recipient">
          <Input
            type="search"
            placeholder="ORD-000123 or name"
            maxLength={SEARCH_MAX_LENGTH}
            value={searchDraft}
            onChange={(event) => {
              setSearchDraft(event.target.value);
              writeSearch(event.target.value);
            }}
            {...fieldAria("notification-search", undefined)}
          />
        </Field>
        <Field id="notification-type" label="Type">
          <Select
            value={filters.notificationType}
            onChange={(event) => updateFilters({ notificationType: event.target.value, page: 1 })}
            {...fieldAria("notification-type", undefined)}
          >
            <option value="">All types</option>
            {NOTIFICATION_TYPES.map((type) => (
              <option key={type} value={type}>
                {NOTIFICATION_TYPE_LABELS[type]}
              </option>
            ))}
          </Select>
        </Field>
      </form>
      <div role="tabpanel" aria-label={TAB_LABELS[filters.tab]} aria-busy={notifications.isFetching} className="flex flex-col gap-4">
        {notifications.isPending ? (
          <p role="status" className="rounded-xl border border-border bg-card px-6 py-16 text-center text-sm text-muted">
            Loading messages…
          </p>
        ) : notifications.isError ? (
          <div role="alert" className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card px-6 py-16 text-center text-sm text-danger">
            <p>{failureMessage(notifications.error, "We could not load messages. Try again.")}</p>
            <Button variant="outline" onClick={() => void notifications.refetch()}>
              Retry
            </Button>
          </div>
        ) : notifications.data.items.length === 0 ? (
          <p role="status" className="rounded-xl border border-dashed border-border-strong px-6 py-16 text-center text-sm text-muted">
            {filters.search || filters.notificationType ? "No messages match your search." : EMPTY_MESSAGES[filters.tab]}
          </p>
        ) : (
          <>
            <ul aria-label={`${TAB_LABELS[filters.tab]} messages`} className="divide-y divide-border rounded-xl border border-border bg-card shadow-xs">
              {notifications.data.items.map((notification) => (
                <NotificationItem key={notification.notificationId} notification={notification} roleCode={roleCode} />
              ))}
            </ul>
            <Pagination
              page={notifications.data.page}
              pageSize={notifications.data.pageSize}
              total={notifications.data.total}
              itemLabel={ITEM_LABEL}
              onPageChange={(page) => updateFilters({ page })}
            />
          </>
        )}
      </div>
    </section>
  );
}
