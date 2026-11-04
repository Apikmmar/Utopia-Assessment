import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { applyServerErrors } from "../form-errors";
import { editUserSchema, normalizePhone, type EditUserValues, type UpdateUserPayload, type User } from "../schemas";
import { UserDetailsFields } from "./user-details-fields";

const FIELDS = ["name", "phone", "age", "roleCode"] as const;

type EditUserFormProps = {
  user: User;
  onSubmit: (payload: UpdateUserPayload) => Promise<void>;
};

// Builds the PATCH payload, sending the role only when it changed.
function toPayload(values: EditUserValues, user: User): UpdateUserPayload {
  const payload: UpdateUserPayload = {
    name: values.name,
    phone: normalizePhone(values.phone) === "" ? null : values.phone.trim(),
    age: values.age.trim() === "" ? null : Number(values.age),
  };
  if (values.roleCode !== user.roleCode) payload.roleCode = values.roleCode;
  return payload;
}

// Form for editing name, phone, age, and role; email and password are not editable here.
export function EditUserForm({ user, onSubmit }: EditUserFormProps) {
  const form = useForm<EditUserValues>({
    resolver: zodResolver(editUserSchema),
    defaultValues: { name: user.name, phone: user.phone ?? "", age: user.age === null ? "" : String(user.age), roleCode: user.roleCode },
  });
  const [formError, setFormError] = useState<string | null>(null);
  const {
    handleSubmit,
    setError,
    formState: { isSubmitting },
  } = form;

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await onSubmit(toPayload(values, user));
    } catch (error) {
      setFormError(applyServerErrors(error, setError, FIELDS));
    }
  });

  return (
    <FormProvider {...form}>
      <form onSubmit={submit} noValidate className="flex max-w-xl flex-col gap-3">
        <UserDetailsFields idPrefix="edit" currentRole={user.roleCode} />
        {formError ? <Alert tone="error">{formError}</Alert> : null}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : "Save changes"}
        </Button>
      </form>
    </FormProvider>
  );
}
