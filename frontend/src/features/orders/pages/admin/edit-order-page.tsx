import { useNavigate, useParams } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { TextLink } from "@/components/ui/text-link";
import { failureMessage } from "@/lib/failure-message";
import { ErrorState, LoadingState } from "../../components/list-states";
import { OrderForm } from "../../components/order-form";
import { toFormValues, toUpdatePayload } from "../../payload";
import { useOrder, useUpdateOrder } from "../../queries";
import { EDITABLE_STATUSES } from "../../statuses";

// Admin edit form for an order's details while it is new or assigned; after the job starts it explains why it is locked.
export function EditOrderPage() {
  const { orderId = "" } = useParams();
  const navigate = useNavigate();
  const detail = useOrder(orderId);
  const update = useUpdateOrder(orderId);
  const back = (
    <TextLink to={`/orders/${orderId}`} className="self-start">
      ← Back to order
    </TextLink>
  );
  if (detail.isPending) return <LoadingState>Loading order…</LoadingState>;
  if (detail.isError) {
    return <ErrorState message={failureMessage(detail.error, "We could not load this order. Try again.")} onRetry={() => void detail.refetch()} />;
  }
  const { order } = detail.data;
  return (
    <section aria-labelledby="edit-order-title" className="flex flex-col gap-6">
      {back}
      <PageHeader id="edit-order-title" title={`Edit ${order.orderNo}`} />
      {(EDITABLE_STATUSES as readonly string[]).includes(order.status) ? (
        <Card>
          <OrderForm
            idPrefix="edit-order"
            defaultValues={toFormValues(order)}
            submitLabel="Save changes"
            pendingLabel="Saving…"
            onSubmit={async (values) => {
              await update.mutateAsync(toUpdatePayload(values));
              navigate(`/orders/${orderId}`);
            }}
          />
        </Card>
      ) : (
        <Alert tone="error">This order can no longer be edited because the job has started.</Alert>
      )}
    </section>
  );
}
