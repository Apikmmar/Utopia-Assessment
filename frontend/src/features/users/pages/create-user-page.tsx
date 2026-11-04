import { Link, useNavigate } from "react-router";
import { CreateUserForm } from "../components/create-user-form";
import { useCreateUser } from "../queries";
import type { CreateUserPayload } from "../schemas";

// Admin page for registering a new user.
export function CreateUserPage() {
  const navigate = useNavigate();
  const create = useCreateUser();

  const submit = async (payload: CreateUserPayload) => {
    await create.mutateAsync(payload);
    navigate("/users", { state: { notice: "User created." } });
  };

  return (
    <section aria-labelledby="create-user-title" className="flex flex-col gap-4">
      <h1 id="create-user-title" className="text-2xl font-semibold">
        New user
      </h1>
      <CreateUserForm onSubmit={submit} />
      <Link to="/users" className="inline-flex min-h-11 items-center text-primary underline">
        Back to users
      </Link>
    </section>
  );
}
