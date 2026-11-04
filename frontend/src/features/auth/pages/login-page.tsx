import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router";
import { PublicShell } from "@/components/layout/public-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, fieldAria } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { TextLink } from "@/components/ui/text-link";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";
import { useLogin } from "../queries";
import { loginSchema, type LoginValues } from "../schemas";

const INVALID_CREDENTIALS_MESSAGE = "Invalid email or password.";
const GENERIC_FAILURE_MESSAGE = "We could not sign you in right now. Please try again.";

// Reads the page the user was sent from, defaulting to the home route.
function redirectTarget(state: unknown) {
  const from = state && typeof state === "object" && "from" in state ? state.from : null;
  return typeof from === "string" && from.startsWith("/") && !from.startsWith("//") ? from : "/";
}

// Login screen with validated email and password fields and one generic failure message.
export function LoginPage() {
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });

  const onSubmit = (values: LoginValues) => {
    login.mutate(values, { onSuccess: () => navigate(redirectTarget(location.state), { replace: true }) });
  };

  const failure = login.error
    ? login.error instanceof ApiError && login.error.code === "INVALID_CREDENTIALS"
      ? INVALID_CREDENTIALS_MESSAGE
      : failureMessage(login.error, GENERIC_FAILURE_MESSAGE)
    : null;

  return (
    <PublicShell>
      <Card>
        <div className="mb-6 flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight">Log in</h1>
          <p className="text-sm text-muted">Use the account your admin set up for you.</p>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
          <Field id="login-email" label="Email" error={errors.email?.message}>
            <Input
              type="email"
              autoComplete="username"
              placeholder="you@company.com"
              {...fieldAria("login-email", errors.email?.message)}
              {...register("email")}
            />
          </Field>
          <Field id="login-password" label="Password" error={errors.password?.message}>
            <Input
              type="password"
              autoComplete="current-password"
              {...fieldAria("login-password", errors.password?.message)}
              {...register("password")}
            />
          </Field>
          {failure ? <Alert tone="error">{failure}</Alert> : null}
          <Button type="submit" className="mt-2 w-full" disabled={login.isPending}>
            {login.isPending ? "Signing in..." : "Log in"}
          </Button>
        </form>
      </Card>
      <TextLink to="/reset-password" className="self-center">
        Forgot your password?
      </TextLink>
    </PublicShell>
  );
}
