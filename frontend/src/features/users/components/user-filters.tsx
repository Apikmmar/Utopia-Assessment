import { Field, fieldAria } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { PAGE_SIZE_OPTIONS, SEARCH_MAX_LENGTH } from "../filters";
import { RoleOptions } from "./role-options";

type UserFiltersProps = {
  search: string;
  roleCode: string;
  pageSize: number;
  onSearchChange: (value: string) => void;
  onRoleChange: (value: string) => void;
  onPageSizeChange: (value: number) => void;
};

// Search box, role filter, and page size for the users list.
export function UserFilters({ search, roleCode, pageSize, onSearchChange, onRoleChange, onPageSizeChange }: UserFiltersProps) {
  return (
    <form role="search" onSubmit={(event) => event.preventDefault()} className="grid gap-3 sm:grid-cols-[1fr_12rem_9rem]">
      <Field id="user-search" label="Search by name or email">
        <Input
          type="search"
          placeholder="Name or email"
          maxLength={SEARCH_MAX_LENGTH}
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          {...fieldAria("user-search", undefined)}
        />
      </Field>
      <Field id="user-role-filter" label="Role">
        <Select value={roleCode} onChange={(event) => onRoleChange(event.target.value)} {...fieldAria("user-role-filter", undefined)}>
          <option value="">All roles</option>
          <RoleOptions />
        </Select>
      </Field>
      <Field id="user-page-size" label="Rows per page">
        <Select value={pageSize} onChange={(event) => onPageSizeChange(Number(event.target.value))} {...fieldAria("user-page-size", undefined)}>
          {PAGE_SIZE_OPTIONS.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </Select>
      </Field>
    </form>
  );
}
