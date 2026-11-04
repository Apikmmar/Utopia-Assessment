import { Link } from "react-router";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMyr } from "../money";
import { formatDateTime } from "../notifications";
import type { OrderListItem } from "../schemas";
import { StatusBadge } from "./status-badge";

// Orders list for admins and managers; the order number links to the order page.
export function OrdersTable({ orders }: { orders: OrderListItem[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Order</TableHead>
          <TableHead>Customer</TableHead>
          <TableHead>Service</TableHead>
          <TableHead>Technician</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Quoted</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {orders.map((order) => (
          <TableRow key={order.orderId}>
            <TableCell>
              <Link to={`/orders/${order.orderId}`} className="font-medium underline-offset-4 hover:underline">
                {order.orderNo}
              </Link>
              <p className="text-xs text-muted">{formatDateTime(order.createdAt)}</p>
            </TableCell>
            <TableCell>
              <p>{order.customerName}</p>
              <p className="max-w-56 truncate text-xs text-muted">{order.address}</p>
            </TableCell>
            <TableCell>{order.serviceType.name}</TableCell>
            <TableCell className={order.technician ? "" : "text-muted"}>{order.technician?.name ?? "Unassigned"}</TableCell>
            <TableCell>
              <StatusBadge status={order.status} />
            </TableCell>
            <TableCell className="text-right whitespace-nowrap tabular-nums">{formatMyr(order.quotedPrice)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
