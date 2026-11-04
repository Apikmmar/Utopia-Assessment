import { ROLE_CODES, ROLE_LABELS, isKnownRole, roleLabel } from "@/features/auth/roles";

// Renders one option per known role, plus the current code when the client does not know it yet.
export function RoleOptions({ current }: { current?: string }) {
  return (
    <>
      {current && !isKnownRole(current) ? <option value={current}>{roleLabel(current)}</option> : null}
      {ROLE_CODES.map((code) => (
        <option key={code} value={code}>
          {ROLE_LABELS[code]}
        </option>
      ))}
    </>
  );
}
