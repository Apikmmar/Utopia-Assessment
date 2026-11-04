import { zodResolver } from "@hookform/resolvers/zod";
import { useRef, useState, type FormEvent } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, fieldAria } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { applyServerErrors } from "../form-errors";
import { generatePassword } from "../password-generator";
import { createUserSchema, normalizePhone, type CreateUserPayload, type CreateUserValues } from "../schemas";
import { UserDetailsFields } from "./user-details-fields";

const FIELDS = ["name", "email", "phone", "age", "roleCode", "password"] as const;

type CreateUserFormProps = {
  onSubmit: (payload: CreateUserPayload) => Promise<void>;
};

// Builds the API payload from validated form values.
function toPayload(values: CreateUserValues): CreateUserPayload {
  const phone = normalizePhone(values.phone) === "" ? undefined : values.phone.trim();
  const age = values.age.trim() === "" ? undefined : Number(values.age);
  return { name: values.name, email: values.email, phone, age, roleCode: values.roleCode, password: values.password };
}

// Form for registering a user, with server errors shown next to their fields.
// A ref guard drops a second submit that lands before the disabled button renders.
export function CreateUserForm({ onSubmit }: CreateUserFormProps) {
  const form = useForm<CreateUserValues>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { name: "", email: "", phone: "", age: "", roleCode: "technician", password: "" },
  });
  const [formError, setFormError] = useState<string | null>(null);
  const inFlight = useRef(false);
  const {
    register,
    handleSubmit,
    setError,
    setValue,
    formState: { errors, isSubmitting },
  } = form;

  const save = async (values: CreateUserValues) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setFormError(null);
    try {
      await onSubmit(toPayload(values));
    } catch (error) {
      setFormError(applyServerErrors(error, setError, FIELDS));
    } finally {
      inFlight.current = false;
    }
  };
  const submit = (event: FormEvent<HTMLFormElement>) => handleSubmit(save)(event);

  const fillPassword = () => setValue("password", generatePassword(), { shouldDirty: true, shouldValidate: true });

  return (
    <FormProvider {...form}>
      <form onSubmit={submit} noValidate className="grid gap-5 sm:grid-cols-2">
        <Field id="create-email" label="Email" error={errors.email?.message} className="sm:col-span-2">
          <Input type="email" autoComplete="off" {...fieldAria("create-email", errors.email?.message)} {...register("email")} />
        </Field>
        <UserDetailsFields idPrefix="create" />
        <Field id="create-password" label="Password" error={errors.password?.message} hint="Use 10 to 128 characters." className="sm:col-span-2">
          <div className="flex gap-2">
            <Input
              type="text"
              autoComplete="new-password"
              spellCheck={false}
              className="font-mono"
              {...fieldAria("create-password", errors.password?.message, true)}
              {...register("password")}
            />
            <Button variant="outline" onClick={fillPassword} className="shrink-0">
              Generate password
            </Button>
          </div>
        </Field>
        {formError ? (
          <div className="sm:col-span-2">
            <Alert tone="error">{formError}</Alert>
          </div>
        ) : null}
        <div className="flex justify-end border-t border-border pt-5 sm:col-span-2">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating..." : "Create user"}
          </Button>
        </div>
      </form>
    </FormProvider>
  );
}
