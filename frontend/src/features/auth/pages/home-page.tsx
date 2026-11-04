import { Navigate } from "react-router";
import { PageHeader } from "@/components/ui/page-header";
import { useMe } from "../queries";
import { isKnownRole, type RoleCode } from "../roles";

const HOME_BY_ROLE: Record<RoleCode, string> = {
  admin: "/orders",
  technician: "/jobs",
  manager: "/review",
};

// Home route: each role goes to its first screen; an unknown role sees a placeholder.
export function HomePage() {
  const me = useMe();
  const user = me.data;
  if (!user) return null;
  if (isKnownRole(user.roleCode)) return <Navigate to={HOME_BY_ROLE[user.roleCode]} replace />;
  return (
    <section aria-labelledby="home-title" className="flex flex-col gap-8">
      <PageHeader id="home-title" title="Home" description={`Welcome, ${user.name}.`} />
      <div className="rounded-xl border border-dashed border-border-strong px-6 py-16 text-center">
        <p className="text-sm text-muted">There are no screens for your role yet.</p>
      </div>
    </section>
  );
}
