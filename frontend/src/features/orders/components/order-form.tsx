import { zodResolver } from "@hookform/resolvers/zod";
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, fieldAria } from "@/components/ui/field";
import { controlClassName, Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/cn";
import { applyServerErrors } from "../form-errors";
import { useServiceTypes } from "../queries";
import { ADDRESS_MAX_LENGTH, ADMIN_NOTES_MAX_LENGTH, orderFormSchema, PROBLEM_MAX_LENGTH, type OrderFormValues, type Technician } from "../schemas";

const FIELDS = ["customerName", "customerPhone", "address", "problemDescription", "serviceTypeId", "quotedPrice", "technicianId", "adminNotes"] as const;
const GENERIC_MESSAGE = "We could not save the order. Please try again.";

export const EMPTY_ORDER_FORM: OrderFormValues = {
  customerName: "",
  customerPhone: "",
  address: "",
  problemDescription: "",
  serviceTypeId: "",
  quotedPrice: "",
  technicianId: "",
  adminNotes: "",
};

type OrderFormProps = {
  idPrefix: string;
  defaultValues: OrderFormValues;
  technicians?: Technician[];
  submitLabel: string;
  pendingLabel: string;
  onSubmit: (values: OrderFormValues) => Promise<void>;
  footer?: ReactNode;
};

// Create and edit form for an order, mirroring the server rules; server field errors land next to their inputs.
// The technician select appears only when technicians are given, and a ref guard drops a second submit.
export function OrderForm({ idPrefix, defaultValues, technicians, submitLabel, pendingLabel, onSubmit, footer }: OrderFormProps) {
  const serviceTypes = useServiceTypes();
  const [formError, setFormError] = useState<string | null>(null);
  const inFlight = useRef(false);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<OrderFormValues>({ resolver: zodResolver(orderFormSchema), defaultValues });
  const id = (name: string) => `${idPrefix}-${name}`;

  const save = async (values: OrderFormValues) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      setFormError(applyServerErrors(error, setError, FIELDS, GENERIC_MESSAGE));
    } finally {
      inFlight.current = false;
    }
  };
  const submit = (event: FormEvent<HTMLFormElement>) => handleSubmit(save)(event);

  return (
    <form onSubmit={submit} noValidate className="grid gap-5 sm:grid-cols-2">
      <Field id={id("customer-name")} label="Customer name" error={errors.customerName?.message}>
        <Input autoComplete="off" {...fieldAria(id("customer-name"), errors.customerName?.message)} {...register("customerName")} />
      </Field>
      <Field id={id("customer-phone")} label="Customer phone" error={errors.customerPhone?.message} hint="For example 012-345 6789.">
        <Input type="tel" inputMode="tel" autoComplete="off" {...fieldAria(id("customer-phone"), errors.customerPhone?.message, true)} {...register("customerPhone")} />
      </Field>
      <Field id={id("address")} label="Service address" error={errors.address?.message} className="sm:col-span-2">
        <textarea
          rows={2}
          maxLength={ADDRESS_MAX_LENGTH}
          className={cn(controlClassName, "py-2")}
          {...fieldAria(id("address"), errors.address?.message)}
          {...register("address")}
        />
      </Field>
      <Field id={id("problem")} label="Problem description" error={errors.problemDescription?.message} className="sm:col-span-2">
        <textarea
          rows={3}
          maxLength={PROBLEM_MAX_LENGTH}
          className={cn(controlClassName, "py-2")}
          {...fieldAria(id("problem"), errors.problemDescription?.message)}
          {...register("problemDescription")}
        />
      </Field>
      <Field id={id("service-type")} label="Service type" error={errors.serviceTypeId?.message ?? (serviceTypes.isError ? "We could not load service types." : undefined)}>
        <Select disabled={serviceTypes.isPending} {...fieldAria(id("service-type"), errors.serviceTypeId?.message)} {...register("serviceTypeId")}>
          <option value="">{serviceTypes.isPending ? "Loading…" : "Choose a service type"}</option>
          {serviceTypes.data?.map((serviceType) => (
            <option key={serviceType.serviceTypeId} value={serviceType.serviceTypeId}>
              {serviceType.name}
            </option>
          ))}
        </Select>
      </Field>
      <Field id={id("quoted-price")} label="Quoted price (RM)" error={errors.quotedPrice?.message}>
        <Input inputMode="decimal" autoComplete="off" placeholder="150.00" {...fieldAria(id("quoted-price"), errors.quotedPrice?.message)} {...register("quotedPrice")} />
      </Field>
      {technicians ? (
        <Field id={id("technician")} label="Technician (optional)" error={errors.technicianId?.message} className="sm:col-span-2">
          <Select {...fieldAria(id("technician"), errors.technicianId?.message)} {...register("technicianId")}>
            <option value="">Assign later</option>
            {technicians.map((technician) => (
              <option key={technician.userId} value={technician.userId}>
                {technician.name}
              </option>
            ))}
          </Select>
        </Field>
      ) : null}
      <Field
        id={id("admin-notes")}
        label="Job instructions (optional)"
        error={errors.adminNotes?.message}
        hint="Shown to the technician, for example access details or parts to bring. Never sent to the customer."
        className="sm:col-span-2"
      >
        <textarea
          rows={3}
          maxLength={ADMIN_NOTES_MAX_LENGTH}
          className={cn(controlClassName, "py-2")}
          {...fieldAria(id("admin-notes"), errors.adminNotes?.message, true)}
          {...register("adminNotes")}
        />
      </Field>
      {formError ? (
        <div className="sm:col-span-2">
          <Alert tone="error">{formError}</Alert>
        </div>
      ) : null}
      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-border pt-5 sm:col-span-2">
        {footer}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? pendingLabel : submitLabel}
        </Button>
      </div>
    </form>
  );
}
