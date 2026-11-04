import type { ReactNode } from "react";
import { NavLink } from "react-router";
import { Badge } from "@/components/ui/badge";
import { BrandMark } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";
import { navigationFor } from "@/features/auth/navigation";
import { useLogout } from "@/features/auth/queries";
import { roleLabel } from "@/features/auth/roles";
import type { AuthUser } from "@/features/auth/schemas";
import { useSendableCount } from "@/features/orders/queries";
import { cn } from "@/lib/cn";
import { useRouteFocus } from "./use-route-focus";

type AppShellProps = { user: AuthUser; children: ReactNode };

// Signed-in layout with role-aware navigation, the user's name, and logout.
export function AppShell({ user, children }: AppShellProps) {
  const mainRef = useRouteFocus();
  const logout = useLogout();
  const navItems = navigationFor(user.roleCode);
  const sendableCount = useSendableCount(navItems.some((item) => item.showSendableCount));
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-border bg-card/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-2 sm:px-6">
          <nav aria-label="Main" className="flex items-center gap-1">
            <BrandMark className="mr-4" />
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-9 items-center rounded-lg px-3 text-sm font-medium transition-colors",
                    isActive ? "bg-subtle text-foreground" : "text-muted hover:text-foreground",
                  )
                }
              >
                {item.label}
                {item.showSendableCount && sendableCount > 0 ? (
                  <span className="ml-1.5 inline-flex min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-medium text-primary-foreground">
                    {sendableCount}
                    <span className="sr-only"> to send</span>
                  </span>
                ) : null}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-2 text-sm sm:flex">
              <span className="font-medium">{user.name}</span>
              <Badge>{roleLabel(user.roleCode)}</Badge>
            </span>
            <Button variant="ghost" className="min-h-9 px-3" onClick={() => logout.mutate()} disabled={logout.isPending}>
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main ref={mainRef} tabIndex={-1} className="mx-auto max-w-5xl px-4 py-10 outline-none sm:px-6">
        {children}
      </main>
    </div>
  );
}
