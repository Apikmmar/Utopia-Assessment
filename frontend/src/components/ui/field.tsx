import type { ReactNode } from "react";
import { Label } from "./label";

type FieldProps = {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
};

// Pairs a visible label and an announced error message with one control.
export function Field({ id, label, error, hint, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint ? (
        <p id={`${id}-hint`} className="text-sm text-muted">
          {hint}
        </p>
      ) : null}
      <p id={`${id}-error`} role="alert" className="min-h-0 text-sm text-danger">
        {error}
      </p>
    </div>
  );
}

// Builds the aria props that connect a control to its hint and error text.
export function fieldAria(id: string, error: string | undefined, hasHint = false) {
  const describedBy = [hasHint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(" ");
  return { id, "aria-invalid": error ? true : undefined, "aria-describedby": describedBy || undefined } as const;
}
