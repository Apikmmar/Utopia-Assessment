import { Navigate, Outlet, useLocation } from "react-router";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { failureMessage } from "@/lib/failure-message";
import { useMe } from "../queries";
import { NotAllowedPage } from "../pages/not-allowed-page";
import type { RoleCode } from "../roles";

type ProtectedRouteProps = { roles?: RoleCode[] };

// Gates a route on the session: loading state, login redirect, then a role check.
export function ProtectedRoute({ roles }: ProtectedRouteProps) {
  const me = useMe();
  const location = useLocation();
  if (me.isPending) {
    return (
      <p role="status" className="p-6 text-sm text-muted">
        Loading your session...
      </p>
    );
  }
  if (me.isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 p-6 text-sm">
        <p>{failureMessage(me.error, "We could not check your session. Try again.")}</p>
        <Button onClick={() => void me.refetch()}>Retry</Button>
      </div>
    );
  }
  if (!me.data) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  const allowed = !roles || (roles as readonly string[]).includes(me.data.roleCode);
  return <AppShell user={me.data}>{allowed ? <Outlet /> : <NotAllowedPage />}</AppShell>;
}
