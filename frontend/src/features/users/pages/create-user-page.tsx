import { useNavigate } from "react-router";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { TextLink } from "@/components/ui/text-link";
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
    <section aria-labelledby="create-user-title" className="flex max-w-2xl flex-col gap-6">
      <TextLink to="/users" className="-mb-4 self-start">
        <span aria-hidden="true" className="mr-1">&larr;</span>
        Back to users
      </TextLink>
      <PageHeader id="create-user-title" title="New user" description="Register an account and choose its role." />
      <Card>
        <CreateUserForm onSubmit={submit} />
      </Card>
    </section>
  );
}
