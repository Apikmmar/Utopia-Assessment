import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { weakPasswordMessage } from "@/features/auth/schemas";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";

const FIELD_FOR_CODE: Record<string, string> = {
  EMAIL_TAKEN: "email",
  SELF_DEMOTE: "roleCode",
};

const PASSWORD_FIELD = "password";
const GENERIC_MESSAGE = "We could not save the user. Please try again.";

// Places server errors on their camelCase fields and returns a form-level message when none match.
export function applyServerErrors<T extends FieldValues>(error: unknown, setError: UseFormSetError<T>, known: readonly string[]) {
  if (!(error instanceof ApiError)) return GENERIC_MESSAGE;
  const entries = Object.entries(error.fields).filter(([name]) => known.includes(name));
  const codeField = FIELD_FOR_CODE[error.code];
  if (codeField && known.includes(codeField) && !error.fields[codeField]) entries.unshift([codeField, error.message]);
  if (entries.length === 0) return error.status === 0 || error.status >= 500 ? failureMessage(error, GENERIC_MESSAGE) : error.message;
  entries.forEach(([name, message], index) => {
    const text = name === PASSWORD_FIELD ? weakPasswordMessage(message) : message;
    setError(name as Path<T>, { type: "server", message: text }, { shouldFocus: index === 0 });
  });
  return null;
}
