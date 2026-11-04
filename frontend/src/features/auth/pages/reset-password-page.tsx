import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import { PublicShell } from "@/components/layout/public-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, fieldAria } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";
import { useResetPassword } from "../queries";
import { resetSchema, weakPasswordMessage, type ResetValues } from "../schemas";

// Reset screen: sets a new password and shows the server's generic confirmation.
export function ResetPasswordPage() {
  const reset = useResetPassword();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetValues>({ resolver: zodResolver(resetSchema), defaultValues: { email: "", newPassword: "" } });

  const onSubmit = (values: ResetValues) => reset.mutate(values);

  const error = reset.error;
  const weak = error instanceof ApiError && error.code === "WEAK_PASSWORD";
  const passwordError = errors.newPassword?.message ?? (weak ? weakPasswordMessage(error.fields.newPassword) : undefined);
  const otherFailure = error && !weak ? failureMessage(error, "We could not reset the password right now. Please try again.") : null;

  return (
    <PublicShell>
      <Card>
        <h1 className="mb-4 text-2xl font-semibold">Reset password</h1>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-3">
          <Field id="reset-email" label="Email" error={errors.email?.message}>
            <Input type="email" autoComplete="username" {...fieldAria("reset-email", errors.email?.message)} {...register("email")} />
          </Field>
          <Field id="reset-password" label="New password" error={passwordError} hint="Use 10 to 128 characters.">
            <Input
              type="password"
              autoComplete="new-password"
              {...fieldAria("reset-password", passwordError, true)}
              {...register("newPassword")}
            />
          </Field>
          {otherFailure ? <Alert tone="error">{otherFailure}</Alert> : null}
          {reset.isSuccess ? <Alert tone="success">{reset.data}</Alert> : null}
          <Button type="submit" disabled={reset.isPending}>
            {reset.isPending ? "Saving..." : "Reset password"}
          </Button>
        </form>
      </Card>
      <p className="text-sm">
        <Link to="/login" className="inline-flex min-h-11 items-center text-primary underline">
          Back to log in
        </Link>
      </p>
    </PublicShell>
  );
}
