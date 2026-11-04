import { Link, useNavigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import { failureMessage } from "@/lib/failure-message";
import { EditUserForm } from "../components/edit-user-form";
import { useUpdateUser, useUser } from "../queries";
import type { UpdateUserPayload } from "../schemas";

// Loads one user and shows the edit form, handling loading and error states.
function EditUserLoaded({ userId }: { userId: string }) {
  const navigate = useNavigate();
  const user = useUser(userId);
  const update = useUpdateUser(userId);

  const submit = async (payload: UpdateUserPayload) => {
    await update.mutateAsync(payload);
    navigate("/users", { state: { notice: "User updated." } });
  };

  if (user.isPending) {
    return (
      <p role="status" className="text-sm text-muted">
        Loading user...
      </p>
    );
  }
  if (user.isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 text-sm text-danger">
        <p>{failureMessage(user.error, "We could not load this user.")}</p>
        <Button variant="outline" onClick={() => void user.refetch()}>
          Retry
        </Button>
      </div>
    );
  }
  return <EditUserForm user={user.data} onSubmit={submit} />;
}

// Admin page for editing a user's name, phone, age, and role.
export function EditUserPage() {
  const { userId = "" } = useParams();
  return (
    <section aria-labelledby="edit-user-title" className="flex flex-col gap-4">
      <h1 id="edit-user-title" className="text-2xl font-semibold">
        Edit user
      </h1>
      <EditUserLoaded userId={userId} />
      <Link to="/users" className="inline-flex min-h-11 items-center text-primary underline">
        Back to users
      </Link>
    </section>
  );
}
