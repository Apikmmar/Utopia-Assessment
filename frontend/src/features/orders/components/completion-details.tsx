import type { ReactNode } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { failureMessage } from "@/lib/failure-message";
import { formatMyr } from "../money";
import { formatDateTime } from "../notifications";
import { useCompletion, useNotifications } from "../queries";
import { paymentMethodLabel, type Completion } from "../schemas";
import { WhatsappButton } from "./whatsapp-button";

// One label and value pair of the completion record.
function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
      <dt className="text-xs font-medium text-muted sm:w-36 sm:shrink-0 sm:text-sm sm:font-normal">{label}</dt>
      <dd className="text-sm break-words whitespace-pre-line">{children}</dd>
    </div>
  );
}

// The stored completion record: work done, amounts against the quote, remarks, payment, and who finished it when.
export function CompletionRecord({ completion }: { completion: Completion }) {
  return (
    <dl className="flex flex-col gap-3">
      <Row label="Work done">{completion.workDone}</Row>
      <Row label="Quoted price">{formatMyr(completion.quotedPrice)}</Row>
      <Row label="Extra charges">{formatMyr(completion.extraCharges)}</Row>
      <Row label="Final amount">
        <strong>{formatMyr(completion.finalAmount)}</strong>
      </Row>
      {completion.remarks ? <Row label="Remarks">{completion.remarks}</Row> : null}
      <Row label="Payment">
        {completion.payment
          ? `${formatMyr(completion.payment.amount)} by ${paymentMethodLabel(completion.payment.method)}${completion.payment.receiptAttachmentId ? ", receipt attached" : ""}`
          : "Not recorded"}
      </Row>
      <Row label="Completed">
        {completion.technician.name}, {formatDateTime(completion.completedAt)}
      </Row>
    </dl>
  );
}

// Loads and shows an order's completion record for the order page; only mounted once the job is done.
export function CompletionDetails({ orderId }: { orderId: string }) {
  const completion = useCompletion(orderId);
  if (completion.isPending) {
    return (
      <p role="status" className="text-sm text-muted">
        Loading completion…
      </p>
    );
  }
  if (completion.isError) {
    return (
      <div role="alert" className="flex items-center gap-3 text-sm text-danger">
        <p>{failureMessage(completion.error, "We could not load the completion record.")}</p>
        <Button variant="outline" onClick={() => void completion.refetch()}>
          Retry
        </Button>
      </div>
    );
  }
  return <CompletionRecord completion={completion.data} />;
}

// Success panel on the job page after completion: the final amount and the button that sends the customer's WhatsApp message.
export function CompletionResult({ orderId }: { orderId: string }) {
  const completion = useCompletion(orderId);
  const notifications = useNotifications({ orderId });
  const customerMessage = notifications.data?.items.find((item) => item.notificationType === "job_done" && item.recipientType === "customer");
  return (
    <Card className="flex flex-col gap-4 p-5 sm:p-6">
      <Alert tone="success">Job completed. Let the customer know on WhatsApp.</Alert>
      {completion.data ? (
        <p className="text-sm">
          Final amount <strong className="text-lg">{formatMyr(completion.data.finalAmount)}</strong>
        </p>
      ) : completion.isError ? (
        <p className="text-sm text-muted">{failureMessage(completion.error, "We could not load the final amount.")}</p>
      ) : null}
      {customerMessage ? <WhatsappButton notification={customerMessage} className="min-h-11 w-full" /> : null}
      {completion.data ? <CompletionRecord completion={completion.data} /> : null}
    </Card>
  );
}
