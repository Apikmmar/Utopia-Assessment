import { Field, fieldAria } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { SEARCH_MAX_LENGTH, type OrderSort } from "../filters";
import type { Technician } from "../schemas";
import { ORDER_STATUSES, ORDER_STATUS_LABELS, type OrderStatus } from "../statuses";

type OrderFiltersProps = {
  search: string;
  status: OrderStatus | "";
  technicianId: string;
  sort: OrderSort;
  technicians?: Technician[];
  onSearchChange: (value: string) => void;
  onStatusChange: (value: OrderStatus | "") => void;
  onTechnicianChange: (value: string) => void;
  onSortChange: (value: OrderSort) => void;
};

// Search, status, technician, and sort controls for the orders list; the technician filter shows only when technicians are given.
export function OrderFilters({
  search,
  status,
  technicianId,
  sort,
  technicians,
  onSearchChange,
  onStatusChange,
  onTechnicianChange,
  onSortChange,
}: OrderFiltersProps) {
  return (
    <form
      role="search"
      onSubmit={(event) => event.preventDefault()}
      className={technicians ? "grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_10rem_12rem_9rem]" : "grid gap-3 sm:grid-cols-[1fr_10rem_9rem]"}
    >
      <Field id="order-search" label="Search by order number or customer">
        <Input
          type="search"
          placeholder="ORD-000123 or name"
          maxLength={SEARCH_MAX_LENGTH}
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          {...fieldAria("order-search", undefined)}
        />
      </Field>
      <Field id="order-status" label="Status">
        <Select value={status} onChange={(event) => onStatusChange(event.target.value as OrderStatus | "")} {...fieldAria("order-status", undefined)}>
          <option value="">All statuses</option>
          {ORDER_STATUSES.map((value) => (
            <option key={value} value={value}>
              {ORDER_STATUS_LABELS[value]}
            </option>
          ))}
        </Select>
      </Field>
      {technicians ? (
        <Field id="order-technician" label="Technician">
          <Select value={technicianId} onChange={(event) => onTechnicianChange(event.target.value)} {...fieldAria("order-technician", undefined)}>
            <option value="">All technicians</option>
            {technicians.map((technician) => (
              <option key={technician.userId} value={technician.userId}>
                {technician.name}
              </option>
            ))}
          </Select>
        </Field>
      ) : null}
      <Field id="order-sort" label="Sort">
        <Select value={sort} onChange={(event) => onSortChange(event.target.value as OrderSort)} {...fieldAria("order-sort", undefined)}>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </Select>
      </Field>
    </form>
  );
}
