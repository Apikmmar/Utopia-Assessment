import { Navigate } from "react-router";
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
    <section aria-labelledby="home-title" className="flex flex-col gap-2">
      <h1 id="home-title" className="text-2xl font-semibold">
        {title}
      </h1>
      <p className="text-muted">Welcome, {user.name}. Your work screens will appear here.</p>
    </section>
  );
}
