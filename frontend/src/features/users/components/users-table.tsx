import { Link } from "react-router";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { roleLabel } from "@/features/auth/roles";
import type { User } from "../schemas";

// Table of users with an edit link per row.
export function UsersTable({ users }: { users: User[] }) {
  return (
    <Table>
      <caption className="sr-only">Users</caption>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Email</TableHead>
          <TableHead>Phone</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>
            <span className="sr-only">Actions</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {users.map((user) => (
          <TableRow key={user.userId}>
            <TableCell>{user.name}</TableCell>
            <TableCell>{user.email}</TableCell>
            <TableCell>{user.phone ?? "-"}</TableCell>
            <TableCell>{roleLabel(user.roleCode)}</TableCell>
            <TableCell>
              <Link
                to={`/users/${user.userId}/edit`}
                aria-label={`Edit ${user.name}`}
                className="inline-flex min-h-11 items-center text-primary underline"
              >
                Edit
              </Link>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
