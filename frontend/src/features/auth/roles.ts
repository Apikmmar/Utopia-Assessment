export const ROLE_CODES = ["admin", "technician", "manager"] as const;

export type RoleCode = (typeof ROLE_CODES)[number];

export const ROLE_LABELS: Record<RoleCode, string> = {
  admin: "Admin",
  technician: "Technician",
  manager: "Manager",
};

const UNKNOWN_ROLE_LABEL = "Unknown role";

// Narrows a server role code to one this client knows.
export function isKnownRole(code: string): code is RoleCode {
  return (ROLE_CODES as readonly string[]).includes(code);
}

// Returns the display label for a role code, falling back for codes this client does not know yet.
export function roleLabel(code: string) {
  if (isKnownRole(code)) return ROLE_LABELS[code];
  return code ? `${UNKNOWN_ROLE_LABEL} (${code})` : UNKNOWN_ROLE_LABEL;
}
