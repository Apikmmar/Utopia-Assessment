import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
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
            <TableCell className="font-medium">{user.name}</TableCell>
            <TableCell className="text-muted">{user.email}</TableCell>
            <TableCell className="text-muted tabular-nums">{user.phone ?? "-"}</TableCell>
            <TableCell>
              <Badge>{roleLabel(user.roleCode)}</Badge>
            </TableCell>
            <TableCell className="text-right">
              <Link
                to={`/users/${user.userId}/edit`}
                aria-label={`Edit ${user.name}`}
                className="inline-flex min-h-9 items-center rounded-lg px-3 text-sm font-medium text-muted transition-colors hover:bg-subtle hover:text-foreground"
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
