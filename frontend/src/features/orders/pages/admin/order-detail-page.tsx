import type { ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { TextLink } from "@/components/ui/text-link";
import { useMe } from "@/features/auth/queries";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";
import { AssignTechnician } from "../../components/assign-technician";
import { AttachmentList } from "../../components/attachment-list";
import { CompletionDetails } from "../../components/completion-details";
import { EventTimeline } from "../../components/event-timeline";
import { ErrorState, LoadingState } from "../../components/list-states";
import { NotificationList } from "../../components/notification-list";
import { OrderSummary } from "../../components/order-summary";
import { StatusActions } from "../../components/status-actions";
import { StatusBadge } from "../../components/status-badge";
import { useOrder } from "../../queries";
import { EDITABLE_STATUSES, FINISHED_JOB_STATUSES } from "../../statuses";

// One titled card section of the order page.
function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="flex flex-col gap-4">
      <h2 className="text-base font-semibold">{title}</h2>
      {children}
    </Card>
  );
}

// Order page for admins and managers: summary, technician, completion, files, WhatsApp messages, and activity, with edit and assign for
// admins and review and close for managers.
export function OrderDetailPage() {
  const { orderId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const roleCode = useMe().data?.roleCode ?? "";
  const detail = useOrder(orderId);
  if (detail.isPending) return <LoadingState>Loading order…</LoadingState>;
  if (detail.isError) {
    if (detail.error instanceof ApiError && detail.error.code === "ORDER_NOT_FOUND") return <Alert tone="error">This order does not exist.</Alert>;
    return <ErrorState message={failureMessage(detail.error, "We could not load this order. Try again.")} onRetry={() => void detail.refetch()} />;
  }
  const { order, events } = detail.data;
  const isAdmin = roleCode === "admin";
  const editable = (EDITABLE_STATUSES as readonly string[]).includes(order.status);

  return (
    <section aria-labelledby="order-title" className="flex flex-col gap-6">
      <TextLink to={roleCode === "manager" && order.status === "job_done" ? "/review" : "/orders"} className="self-start">
        ← Back to {roleCode === "manager" && order.status === "job_done" ? "review" : "orders"}
      </TextLink>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 id="order-title" className="text-2xl font-semibold tracking-tight">
            {order.orderNo}
          </h1>
          <StatusBadge status={order.status} />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {isAdmin && editable ? (
            <Button variant="outline" asChild>
              <Link to={`/orders/${order.orderId}/edit`}>Edit details</Link>
            </Button>
          ) : null}
          <StatusActions order={order} roleCode={roleCode} />
        </div>
      </div>
      {searchParams.get("created") === "1" ? (
        <Alert tone="success">
          Order {order.orderNo} created.{order.technician ? " Send the job to the technician on WhatsApp below." : " Assign a technician when ready."}
        </Alert>
      ) : null}
      <Section title="Order">
        <OrderSummary order={order} />
      </Section>
      {isAdmin && editable ? (
        <Section title="Technician">
          <AssignTechnician key={order.technician?.userId ?? "none"} order={order} />
        </Section>
      ) : null}
      {(FINISHED_JOB_STATUSES as readonly string[]).includes(order.status) ? (
        <Section title="Completion">
          <CompletionDetails orderId={order.orderId} />
        </Section>
      ) : null}
      {(FINISHED_JOB_STATUSES as readonly string[]).includes(order.status) ? (
        <Section title="Files">
          <AttachmentList orderId={order.orderId} />
        </Section>
      ) : null}
      <Section title="WhatsApp messages">
        <NotificationList orderId={order.orderId} roleCode={roleCode} />
      </Section>
      <Section title="Activity">
        <EventTimeline events={events} />
      </Section>
    </section>
  );
}
