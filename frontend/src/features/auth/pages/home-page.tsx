import { Navigate } from "react-router";
import { PageHeader } from "@/components/ui/page-header";
import { useMe } from "../queries";
import { ROLE_LABELS, isKnownRole } from "../roles";

// Home route: admins go to Users; other roles, including unknown ones, see a placeholder.
export function HomePage() {
  const me = useMe();
  const user = me.data;
  if (!user) return null;
  if (user.roleCode === "admin") return <Navigate to="/users" replace />;
  const title = isKnownRole(user.roleCode) ? `${ROLE_LABELS[user.roleCode]} home` : "Home";
  return (
    <section aria-labelledby="home-title" className="flex flex-col gap-8">
      <PageHeader id="home-title" title={title} description={`Welcome, ${user.name}.`} />
      <div className="rounded-xl border border-dashed border-border-strong px-6 py-16 text-center">
        <p className="text-sm text-muted">Your work screens will appear here.</p>
      </div>
    </section>
  );
}
