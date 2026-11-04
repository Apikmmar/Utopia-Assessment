import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, fieldAria } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";
import { useAssignTechnician, useTechnicians } from "../queries";
import type { Order } from "../schemas";

// Technician select with a save button for an order that is still new or assigned.
export function AssignTechnician({ order }: { order: Order }) {
  const technicians = useTechnicians();
  const assign = useAssignTechnician(order.orderId);
  const [technicianId, setTechnicianId] = useState(order.technician?.userId ?? "");
  const unchanged = technicianId === (order.technician?.userId ?? "");
  const error = assign.error instanceof ApiError && assign.error.status < 500 ? assign.error.message : assign.isError ? failureMessage(assign.error, "We could not assign the technician. Try again.") : null;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (technicianId && !unchanged) assign.mutate(technicianId);
      }}
      className="flex flex-col gap-3"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <Field id="assign-technician" label={order.technician ? "Change technician" : "Assign a technician"} className="flex-1">
          <Select
            value={technicianId}
            disabled={technicians.isPending}
            onChange={(event) => setTechnicianId(event.target.value)}
            {...fieldAria("assign-technician", undefined)}
          >
            <option value="">{technicians.isPending ? "Loading…" : "Choose a technician"}</option>
            {technicians.data?.map((technician) => (
              <option key={technician.userId} value={technician.userId}>
                {technician.name}
              </option>
            ))}
          </Select>
        </Field>
        <Button type="submit" disabled={!technicianId || unchanged || assign.isPending}>
          {assign.isPending ? "Saving…" : order.technician ? "Reassign" : "Assign"}
        </Button>
      </div>
      {assign.isSuccess && !assign.isPending ? <Alert tone="success">Technician saved. Send them the job on WhatsApp below.</Alert> : null}
      {error ? <Alert tone="error">{error}</Alert> : null}
    </form>
  );
}
