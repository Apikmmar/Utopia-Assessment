import { Button } from "./button";

type PaginationProps = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  itemLabel?: { one: string; many: string };
};

const DEFAULT_ITEM_LABEL = { one: "user", many: "users" };

// Previous and next controls with a page summary, driven by server totals.
export function Pagination({ page, pageSize, total, onPageChange, itemLabel = DEFAULT_ITEM_LABEL }: PaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-muted" aria-live="polite">
        Page {page} of {pageCount} ({total} {total === 1 ? itemLabel.one : itemLabel.many})
      </p>
      <div className="flex gap-2">
        <Button variant="outline" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </Button>
        <Button variant="outline" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>
          Next
        </Button>
      </div>
    </nav>
  );
}
