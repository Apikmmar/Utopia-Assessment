import { useRef, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, fieldAria } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";
import { addDays, businessToday, POSTPONE_MAX_DAYS_AHEAD, POSTPONE_REASON_LABELS, POSTPONE_REASONS } from "../postpone";
import { usePostponeOrder } from "../queries";
import type { Order } from "../schemas";

const CHANGED_MESSAGE = "This order's status changed in the meantime, so the visit was not postponed. The page now shows its current status.";
const GENERIC_MESSAGE = "We could not postpone the visit. Try again.";

type FieldErrors = { reasonCode?: string; newDate?: string };

// Returns the field errors and form message for a failed postponement.
function failure(error: unknown): { fields: FieldErrors; message: string | null } {
  if (!(error instanceof ApiError)) return { fields: {}, message: failureMessage(error, GENERIC_MESSAGE) };
  if (error.code === "INVALID_TRANSITION") return { fields: {}, message: CHANGED_MESSAGE };
  const fields = { reasonCode: error.fields.reasonCode, newDate: error.fields.newDate };
  if (fields.reasonCode || fields.newDate) return { fields, message: null };
  return { fields: {}, message: error.status === 0 || error.status >= 500 ? failureMessage(error, GENERIC_MESSAGE) : error.message };
}

// "Postpone visit" button that opens a small form with a reason and an optional new date; the order keeps its status.
export function PostponeVisit({ order }: { order: Order }) {
  const postpone = usePostponeOrder(order.orderId);
  const submitting = useRef(false);
  const [open, setOpen] = useState(false);
  const [reasonCode, setReasonCode] = useState("");
  const [newDate, setNewDate] = useState("");
  const [reasonError, setReasonError] = useState<string>();
  const [saved, setSaved] = useState(false);
  const today = businessToday();
  const server = postpone.isError ? failure(postpone.error) : { fields: {} as FieldErrors, message: null };
  const reasonMessage = reasonError ?? server.fields.reasonCode;

  // Validates the reason, then sends one request even when clicked twice.
  function submit() {
    if (!reasonCode) {
      setReasonError("Choose a reason.");
      return;
    }
    if (submitting.current) return;
    submitting.current = true;
    setReasonError(undefined);
    postpone.mutate(
      { reasonCode, ...(newDate ? { newDate } : {}) },
      {
        onSuccess: () => {
          setOpen(false);
          setSaved(true);
          setReasonCode("");
          setNewDate("");
        },
        onSettled: () => {
          submitting.current = false;
        },
      },
    );
  }

  if (!open) {
    return (
      <div className="flex flex-col gap-3">
        <Button
          variant="outline"
          className="min-h-11 w-full sm:w-auto sm:self-start"
          onClick={() => {
            setSaved(false);
            postpone.reset();
            setOpen(true);
          }}
        >
          Postpone visit
        </Button>
        {saved ? <Alert tone="success">Visit postponed. It is recorded in the order activity.</Alert> : null}
        {server.message ? <Alert tone="error">{server.message}</Alert> : null}
      </div>
    );
  }

  return (
    <form
      aria-label="Postpone visit"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className="flex flex-col gap-4 rounded-xl border border-border bg-card p-4"
    >
      <h2 className="text-base font-semibold">Postpone visit</h2>
      <Field id="postpone-reason" label="Reason" error={reasonMessage}>
        <Select value={reasonCode} onChange={(event) => setReasonCode(event.target.value)} {...fieldAria("postpone-reason", reasonMessage)}>
          <option value="">Choose a reason</option>
          {POSTPONE_REASONS.map((code) => (
            <option key={code} value={code}>
              {POSTPONE_REASON_LABELS[code]}
            </option>
          ))}
        </Select>
      </Field>
      <Field id="postpone-date" label="New date (optional)" error={server.fields.newDate} hint={`Up to ${POSTPONE_MAX_DAYS_AHEAD} days ahead.`}>
        <Input
          type="date"
          value={newDate}
          min={today}
          max={addDays(today, POSTPONE_MAX_DAYS_AHEAD)}
          onChange={(event) => setNewDate(event.target.value)}
          {...fieldAria("postpone-date", server.fields.newDate, true)}
        />
      </Field>
      {server.message ? <Alert tone="error">{server.message}</Alert> : null}
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button type="submit" className="min-h-11" disabled={postpone.isPending}>
          {postpone.isPending ? "Saving…" : "Save postponement"}
        </Button>
        <Button variant="ghost" className="min-h-11" disabled={postpone.isPending} onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
