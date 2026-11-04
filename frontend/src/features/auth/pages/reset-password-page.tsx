import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { PublicShell } from "@/components/layout/public-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, fieldAria } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { TextLink } from "@/components/ui/text-link";
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
        <div className="mb-6 flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight">Reset password</h1>
          <p className="text-sm text-muted">Enter your email and choose a new password.</p>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
          <Field id="reset-email" label="Email" error={errors.email?.message}>
            <Input
              type="email"
              autoComplete="username"
              placeholder="you@company.com"
              {...fieldAria("reset-email", errors.email?.message)}
              {...register("email")}
            />
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
          <Button type="submit" className="mt-2 w-full" disabled={reset.isPending}>
            {reset.isPending ? "Saving..." : "Reset password"}
          </Button>
        </form>
      </Card>
      <TextLink to="/login" className="self-center">
        Back to log in
      </TextLink>
    </PublicShell>
  );
}
