import { useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { failureMessage } from "@/lib/failure-message";
import { UserFilters } from "../components/user-filters";
import { UsersTable } from "../components/users-table";
import { readUserFilters, toUserFilterParams } from "../filters";
import { useDebouncedCallback } from "../hooks/use-debounced-callback";
import { useUsers } from "../queries";
import type { UserListFilters } from "../types";

const SEARCH_DEBOUNCE_MS = 300;
const LOAD_FAILURE_MESSAGE = "We could not load users. Try again.";

// Admin users list whose search, role, page, and page size live in the URL so refresh and back keep them.
// Typing updates a local draft at once and writes the search to the URL after a short pause.
export function UsersPage() {
  const location = useLocation();
  const notice = location.state && typeof location.state === "object" && "notice" in location.state ? String(location.state.notice) : null;
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = readUserFilters(searchParams);
  const [searchDraft, setSearchDraft] = useState(filters.search);
  const [syncedSearch, setSyncedSearch] = useState(filters.search);
  if (syncedSearch !== filters.search) {
    setSyncedSearch(filters.search);
    setSearchDraft(filters.search);
  }
  const users = useUsers(filters);

  const updateFilters = (changes: Partial<UserListFilters>, replace = false) => {
    setSearchParams((current) => toUserFilterParams({ ...readUserFilters(current), ...changes }), { replace });
  };
  const writeSearch = useDebouncedCallback((value: string) => updateFilters({ search: value, page: 1 }, true), SEARCH_DEBOUNCE_MS);

  const changeSearch = (value: string) => {
    setSearchDraft(value);
    writeSearch(value);
  };

  return (
    <section aria-labelledby="users-title" className="flex flex-col gap-6">
      <PageHeader
        id="users-title"
        title="Users"
        description="Manage who can sign in and what they can do."
        actions={
          <Button asChild>
            <Link to="/users/new">New user</Link>
          </Button>
        }
      />
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      <UserFilters
        search={searchDraft}
        roleCode={filters.roleCode}
        pageSize={filters.pageSize}
        onSearchChange={changeSearch}
        onRoleChange={(roleCode) => updateFilters({ roleCode, page: 1 })}
        onPageSizeChange={(pageSize) => updateFilters({ pageSize, page: 1 })}
      />
      <div aria-busy={users.isFetching} className="flex flex-col gap-4">
        {users.isPending ? (
          <p role="status" className="rounded-xl border border-border bg-card px-6 py-16 text-center text-sm text-muted">
            Loading users...
          </p>
        ) : users.isError ? (
          <div role="alert" className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card px-6 py-16 text-center text-sm text-danger">
            <p>{failureMessage(users.error, LOAD_FAILURE_MESSAGE)}</p>
            <Button variant="outline" onClick={() => void users.refetch()}>
              Retry
            </Button>
          </div>
        ) : users.data.items.length === 0 ? (
          <p role="status" className="rounded-xl border border-dashed border-border-strong px-6 py-16 text-center text-sm text-muted">
            No users match your search.
          </p>
        ) : (
          <>
            <UsersTable users={users.data.items} />
            <Pagination
              page={users.data.page}
              pageSize={users.data.pageSize}
              total={users.data.total}
              onPageChange={(page) => updateFilters({ page })}
            />
          </>
        )}
      </div>
    </section>
  );
}
