import { Link } from "react-router";
import type { OrderListItem } from "../schemas";
import { StatusBadge } from "./status-badge";

// One job in the technician's list: the whole card is a large touch target leading to the job page.
export function JobCard({ job }: { job: OrderListItem }) {
  return (
    <li>
      <Link
        to={`/jobs/${job.orderId}`}
        className="flex min-h-11 flex-col gap-2 rounded-xl border border-border bg-card p-4 shadow-xs transition-colors hover:border-border-strong"
      >
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium">{job.orderNo}</span>
          <StatusBadge status={job.status} />
        </div>
        <p className="text-sm">{job.customerName}</p>
        <p className="text-sm text-muted">{job.address}</p>
        <p className="text-xs text-muted">{job.serviceType.name}</p>
      </Link>
    </li>
  );
}
