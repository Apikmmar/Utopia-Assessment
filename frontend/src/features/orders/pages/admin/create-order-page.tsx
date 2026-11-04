import { useNavigate } from "react-router";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { TextLink } from "@/components/ui/text-link";
import { EMPTY_ORDER_FORM, OrderForm } from "../../components/order-form";
import { toCreatePayload } from "../../payload";
import { useCreateOrder, useTechnicians } from "../../queries";

// Admin page for a new order; on success it opens the order with a created notice and the technician's WhatsApp button.
export function CreateOrderPage() {
  const navigate = useNavigate();
  const create = useCreateOrder();
  const technicians = useTechnicians();
  return (
    <section aria-labelledby="create-order-title" className="flex flex-col gap-6">
      <TextLink to="/orders" className="self-start">
        ← Back to orders
      </TextLink>
      <PageHeader id="create-order-title" title="New order" description="Record the customer's request and, if you can, assign a technician now." />
      <Card>
        <OrderForm
          idPrefix="create-order"
          defaultValues={EMPTY_ORDER_FORM}
          technicians={technicians.data ?? []}
          submitLabel="Create order"
          pendingLabel="Creating…"
          onSubmit={async (values) => {
            const result = await create.mutateAsync(toCreatePayload(values));
            navigate(`/orders/${result.order.orderId}?created=1`);
          }}
        />
      </Card>
    </section>
  );
}
