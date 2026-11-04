import { isKnownRole, type RoleCode } from "./roles";

export type NavItem = { to: string; label: string };

const NAV_BY_ROLE: Record<RoleCode, NavItem[]> = {
  admin: [{ to: "/users", label: "Users" }],
  technician: [{ to: "/", label: "Home" }],
  manager: [{ to: "/", label: "Home" }],
};

const FALLBACK_NAV: NavItem[] = [{ to: "/", label: "Home" }];

// Returns only the navigation entries a role may use; an unknown role gets the home link only.
export function navigationFor(role: string): NavItem[] {
  return isKnownRole(role) ? NAV_BY_ROLE[role] : FALLBACK_NAV;
}
