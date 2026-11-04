import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";

const FIELD_FOR_CODE: Record<string, string> = {
  INVALID_SERVICE_TYPE: "serviceTypeId",
  INVALID_TECHNICIAN: "technicianId",
};

// Places server errors on their camelCase fields, renamed through aliases such as payment.amount to paymentAmount, and
// returns a form-level message when none match the form.
export function applyServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  known: readonly string[],
  genericMessage: string,
  aliases: Record<string, string> = {},
) {
  if (!(error instanceof ApiError)) return genericMessage;
  const entries = Object.entries(error.fields)
    .map(([name, message]): [string, string] => [aliases[name] ?? name, message])
    .filter(([name]) => known.includes(name));
  const codeField = FIELD_FOR_CODE[error.code];
  if (codeField && known.includes(codeField) && !error.fields[codeField]) entries.unshift([codeField, error.message]);
  if (entries.length === 0) return error.status === 0 || error.status >= 500 ? failureMessage(error, genericMessage) : error.message;
  entries.forEach(([name, message], index) => {
    setError(name as Path<T>, { type: "server", message }, { shouldFocus: index === 0 });
  });
  return null;
}
