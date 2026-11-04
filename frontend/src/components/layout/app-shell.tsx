import type { ReactNode } from "react";
import { NavLink } from "react-router";
import { Button } from "@/components/ui/button";
import { navigationFor } from "@/features/auth/navigation";
import { useLogout } from "@/features/auth/queries";
import { roleLabel } from "@/features/auth/roles";
import type { AuthUser } from "@/features/auth/schemas";
import { cn } from "@/lib/cn";
import { useRouteFocus } from "./use-route-focus";

type AppShellProps = { user: AuthUser; children: ReactNode };

// Signed-in layout with role-aware navigation, the user's name, and logout.
export function AppShell({ user, children }: AppShellProps) {
  const mainRef = useRouteFocus();
  const logout = useLogout();
  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-2">
          <nav aria-label="Main" className="flex items-center gap-1">
            <span className="mr-3 text-base font-semibold">Utopia</span>
            {navigationFor(user.roleCode).map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn("flex min-h-11 items-center rounded-md px-3 text-sm font-medium", isActive ? "bg-slate-200" : "hover:bg-slate-100")
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted">
              {user.name} ({roleLabel(user.roleCode)})
            </span>
            <Button variant="outline" onClick={() => logout.mutate()} disabled={logout.isPending}>
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main ref={mainRef} tabIndex={-1} className="mx-auto max-w-6xl px-4 py-6 outline-none">
        {children}
      </main>
    </div>
  );
}
