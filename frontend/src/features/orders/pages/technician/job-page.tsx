import type { ReactNode } from "react";
import { useParams } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { TextLink } from "@/components/ui/text-link";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";
import { AttachmentList } from "../../components/attachment-list";
import { CompletionResult } from "../../components/completion-details";
import { CompletionForm } from "../../components/completion-form";
import { ErrorState, LoadingState } from "../../components/list-states";
import { NotificationList } from "../../components/notification-list";
import { StatusActions } from "../../components/status-actions";
import { StatusBadge } from "../../components/status-badge";
import { formatMyr } from "../../money";
import { formatDateTime } from "../../notifications";
import { useAttachments, useOrder } from "../../queries";
import type { Order } from "../../schemas";
import { FINISHED_JOB_STATUSES } from "../../statuses";

const MAPS_SEARCH_URL = "https://www.google.com/maps/search/?api=1&query=";

// One labelled block of the job page.
function Block({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <h2 className="text-xs font-medium text-muted">{label}</h2>
      <div className="text-sm break-words whitespace-pre-line">{children}</div>
    </div>
  );
}

// The completion form for a job in progress, mounted once the job's pending files are known so uploads from before a
// reload come back; if the file list cannot load, the form still opens without them.
function CompletionSection({ order }: { order: Order }) {
  const attachments = useAttachments(order.orderId);
  if (attachments.isPending) return <LoadingState>Loading completion form…</LoadingState>;
  return <CompletionForm order={order} existing={attachments.data ?? []} />;
}

// Technician job page in the order a visit needs it: customer and phone, address and map, problem, instructions,
// price, then the action for the current status.
export function JobPage() {
  const { orderId = "" } = useParams();
  const detail = useOrder(orderId);
  if (detail.isPending) return <LoadingState>Loading job…</LoadingState>;
  if (detail.isError) {
    if (detail.error instanceof ApiError && detail.error.code === "ORDER_NOT_FOUND") return <Alert tone="error">This job is not assigned to you.</Alert>;
    return <ErrorState message={failureMessage(detail.error, "We could not load this job. Try again.")} onRetry={() => void detail.refetch()} />;
  }
  const { order } = detail.data;
  return (
    <section aria-labelledby="job-title" className="mx-auto flex w-full max-w-xl flex-col gap-6 pb-24 sm:pb-0">
      <TextLink to="/jobs" className="self-start">
        ← My jobs
      </TextLink>
      <div className="flex items-center justify-between gap-3">
        <h1 id="job-title" className="text-2xl font-semibold tracking-tight">
          {order.orderNo}
        </h1>
        <StatusBadge status={order.status} />
      </div>
      <Card className="flex flex-col gap-5 p-5 sm:p-6">
        <Block label="Customer">
          <p>{order.customerName}</p>
          <a href={`tel:+${order.customerPhone}`} className="mt-2 inline-flex min-h-11 items-center font-medium underline underline-offset-4">
            Call {order.customerPhone}
          </a>
        </Block>
        <Block label="Address">
          <p>{order.address}</p>
          <a
            href={`${MAPS_SEARCH_URL}${encodeURIComponent(order.address)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-flex min-h-11 items-center font-medium underline underline-offset-4"
          >
            Open in Maps
          </a>
        </Block>
        <Block label="Problem">{order.problemDescription}</Block>
        {order.adminNotes ? <Block label="Job instructions">{order.adminNotes}</Block> : null}
        <Block label="Service">{order.serviceType.name}</Block>
        <Block label="Quoted price">{formatMyr(order.quotedPrice)}</Block>
        {order.startedAt ? <Block label="Started">{formatDateTime(order.startedAt)}</Block> : null}
      </Card>
      {order.status === "assigned" ? (
        <div className="fixed inset-x-0 bottom-0 z-10 border-t border-border bg-card/95 p-4 backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0">
          <StatusActions order={order} roleCode="technician" className="min-h-11 w-full" />
        </div>
      ) : null}
      {order.status === "in_progress" ? <CompletionSection order={order} /> : null}
      {(FINISHED_JOB_STATUSES as readonly string[]).includes(order.status) ? <CompletionResult orderId={order.orderId} /> : null}
      {(FINISHED_JOB_STATUSES as readonly string[]).includes(order.status) ? (
        <div className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">Files</h2>
          <AttachmentList orderId={order.orderId} />
        </div>
      ) : null}
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">WhatsApp messages</h2>
        <NotificationList orderId={order.orderId} roleCode="technician" />
      </div>
    </section>
  );
}
