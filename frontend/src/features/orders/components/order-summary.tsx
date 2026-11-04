import type { ReactNode } from "react";
import { formatMyr } from "../money";
import { formatDateTime } from "../notifications";
import type { Order } from "../schemas";

// One label and value pair in the summary list.
function Item({ label, children, wide = false }: { label: string; children: ReactNode; wide?: boolean }) {
  return (
    <div className={wide ? "sm:col-span-2" : undefined}>
      <dt className="text-xs font-medium text-muted">{label}</dt>
      <dd className="mt-1 text-sm break-words whitespace-pre-line">{children}</dd>
    </div>
  );
}

// Customer, service, price, technician, and job instructions of one order.
export function OrderSummary({ order }: { order: Order }) {
  return (
    <dl className="grid gap-5 sm:grid-cols-2">
      <Item label="Customer">{order.customerName}</Item>
      <Item label="Phone">{order.customerPhone}</Item>
      <Item label="Address" wide>
        {order.address}
      </Item>
      <Item label="Problem" wide>
        {order.problemDescription}
      </Item>
      <Item label="Service type">{order.serviceType.name}</Item>
      <Item label="Quoted price">{formatMyr(order.quotedPrice)}</Item>
      <Item label="Technician">{order.technician ? `${order.technician.name}${order.technician.phone ? ` · ${order.technician.phone}` : ""}` : "Unassigned"}</Item>
      <Item label="Created">{formatDateTime(order.createdAt)}</Item>
      {order.adminNotes ? (
        <Item label="Job instructions" wide>
          {order.adminNotes}
        </Item>
      ) : null}
    </dl>
  );
}
