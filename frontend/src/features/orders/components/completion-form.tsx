import { zodResolver } from "@hookform/resolvers/zod";
import { useRef, useState, type FormEvent } from "react";
import { useForm } from "react-hook-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, fieldAria } from "@/components/ui/field";
import { controlClassName, Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/cn";
import { applyServerErrors } from "../form-errors";
import { useFileUpload } from "../hooks/use-file-upload";
import { finalAmountPreview, formatMyr } from "../money";
import { useSubmitCompletion } from "../queries";
import {
  completionFormSchema,
  PAYMENT_METHOD_LABELS,
  PAYMENT_METHODS,
  REMARKS_MAX_LENGTH,
  WORK_DONE_MAX_LENGTH,
  type Attachment,
  type CompletionFormValues,
  type Order,
  type SubmitCompletionPayload,
} from "../schemas";
import { FileUploader } from "./file-uploader";

const FIELDS = ["workDone", "extraCharges", "remarks", "paymentAmount", "paymentMethod"] as const;
const SERVER_FIELD_ALIASES = { "payment.amount": "paymentAmount", "payment.method": "paymentMethod" };
const GENERIC_MESSAGE = "We could not save the completion. Your details are kept, so try again.";
const EMPTY_VALUES: CompletionFormValues = { workDone: "", extraCharges: "", remarks: "", paymentEnabled: false, paymentAmount: "", paymentMethod: "" };

type CompletionFormProps = { order: Order; existing: Attachment[] };

// Builds the submit payload from validated values and the finished uploads; the receipt goes only with a payment.
export function toCompletionPayload(values: CompletionFormValues, attachmentIds: string[], receiptId: string | undefined): SubmitCompletionPayload {
  const payload: SubmitCompletionPayload = { workDone: values.workDone.trim(), extraCharges: values.extraCharges.trim() || "0", attachmentIds };
  const remarks = values.remarks.trim();
  if (remarks) payload.remarks = remarks;
  if (values.paymentEnabled) {
    payload.payment = { amount: values.paymentAmount.trim(), method: values.paymentMethod, ...(receiptId ? { receiptAttachmentId: receiptId } : {}) };
  }
  return payload;
}

// Completion form for the assigned technician: work done, extra charges with a final amount preview, remarks, files,
// and an optional payment. Submit waits for every upload, a ref guard drops a second submit, and input survives failures.
export function CompletionForm({ order, existing }: CompletionFormProps) {
  const files = useFileUpload(order.orderId, "completion", existing);
  const receipt = useFileUpload(order.orderId, "receipt", existing);
  const submitCompletion = useSubmitCompletion(order.orderId);
  const [formError, setFormError] = useState<string | null>(null);
  const inFlight = useRef(false);
  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CompletionFormValues>({ resolver: zodResolver(completionFormSchema), defaultValues: EMPTY_VALUES });
  const paymentEnabled = watch("paymentEnabled");
  const preview = finalAmountPreview(order.quotedPrice, watch("extraCharges"));
  const uploadsFailed = files.hasFailed || (paymentEnabled && receipt.hasFailed);
  const uploadsBusy = uploadsFailed || files.isUploading || (paymentEnabled && receipt.isUploading);
  const busy = submitCompletion.isPending || inFlight.current;

  const save = async (values: CompletionFormValues) => {
    if (inFlight.current || uploadsBusy) return;
    inFlight.current = true;
    setFormError(null);
    try {
      await submitCompletion.mutateAsync(toCompletionPayload(values, files.doneIds, values.paymentEnabled ? receipt.doneIds[0] : undefined));
    } catch (error) {
      setFormError(applyServerErrors(error, setError, FIELDS, GENERIC_MESSAGE, SERVER_FIELD_ALIASES));
    } finally {
      inFlight.current = false;
    }
  };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    if (inFlight.current) {
      event.preventDefault();
      return;
    }
    void handleSubmit(save)(event);
  };

  return (
    <form onSubmit={submit} noValidate aria-labelledby="completion-title" className="flex flex-col gap-5">
      <Card className="flex flex-col gap-5 p-5 sm:p-6">
        <h2 id="completion-title" className="text-base font-semibold">
          Complete {order.orderNo}
        </h2>
        <Field id="completion-work-done" label="Work done" error={errors.workDone?.message}>
          <textarea
            rows={4}
            maxLength={WORK_DONE_MAX_LENGTH}
            className={cn(controlClassName, "py-2")}
            {...fieldAria("completion-work-done", errors.workDone?.message)}
            {...register("workDone")}
          />
        </Field>
        <Field id="completion-extra" label="Extra charges (RM)" error={errors.extraCharges?.message} hint="Leave blank when there are none.">
          <Input inputMode="decimal" autoComplete="off" placeholder="0.00" className="min-h-11" {...fieldAria("completion-extra", errors.extraCharges?.message, true)} {...register("extraCharges")} />
        </Field>
        <div className="flex items-center justify-between rounded-lg bg-subtle px-4 py-3 text-sm">
          <span className="text-muted">Quoted {formatMyr(order.quotedPrice)} + extra charges</span>
          <span aria-live="polite">
            Final amount <strong data-testid="final-amount-preview">{preview ? formatMyr(preview) : "—"}</strong>
          </span>
        </div>
        <Field id="completion-remarks" label="Remarks (optional)" error={errors.remarks?.message}>
          <textarea
            rows={2}
            maxLength={REMARKS_MAX_LENGTH}
            className={cn(controlClassName, "py-2")}
            {...fieldAria("completion-remarks", errors.remarks?.message)}
            {...register("remarks")}
          />
        </Field>
        <FileUploader upload={files} label="Photos, videos, or PDFs" hint="Up to 6 files. Images and PDFs up to 10 MB, videos up to 49 MB." />
      </Card>
      <Card className="flex flex-col gap-5 p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold">Payment (optional)</h2>
          <Button variant="outline" className="min-h-11" aria-expanded={paymentEnabled} onClick={() => setValue("paymentEnabled", !paymentEnabled)}>
            {paymentEnabled ? "Remove payment" : "Record a payment"}
          </Button>
        </div>
        {paymentEnabled ? (
          <>
            <Field id="completion-payment-amount" label="Amount paid (RM)" error={errors.paymentAmount?.message}>
              <Input inputMode="decimal" autoComplete="off" className="min-h-11" {...fieldAria("completion-payment-amount", errors.paymentAmount?.message)} {...register("paymentAmount")} />
            </Field>
            <Field id="completion-payment-method" label="Payment method" error={errors.paymentMethod?.message}>
              <Select className="min-h-11" {...fieldAria("completion-payment-method", errors.paymentMethod?.message)} {...register("paymentMethod")}>
                <option value="">Choose a method</option>
                {PAYMENT_METHODS.map((method) => (
                  <option key={method} value={method}>
                    {PAYMENT_METHOD_LABELS[method]}
                  </option>
                ))}
              </Select>
            </Field>
            <FileUploader upload={receipt} label="Receipt (optional)" />
          </>
        ) : null}
      </Card>
      {formError ? <Alert tone="error">{formError}</Alert> : null}
      <div className="fixed inset-x-0 bottom-0 z-10 border-t border-border bg-card/95 p-4 backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0">
        <Button type="submit" className="min-h-11 w-full" disabled={busy || uploadsBusy}>
          {busy ? "Submitting…" : uploadsFailed ? "Retry or remove failed files" : uploadsBusy ? "Waiting for files…" : "Submit completion"}
        </Button>
      </div>
    </form>
  );
}
