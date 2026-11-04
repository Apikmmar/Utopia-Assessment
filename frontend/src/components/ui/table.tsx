import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

// Table inside a bordered surface that scrolls horizontally on narrow screens.
export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
      <table className={cn("w-full text-left text-sm", className)} {...props} />
    </div>
  );
}

// Table header group.
export function TableHeader(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className="border-b border-border bg-zinc-50/70" {...props} />;
}

// Table body group.
export function TableBody(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className="[&_tr]:hover:bg-zinc-50/70" {...props} />;
}

// Table row with a hairline divider.
export function TableRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("border-b border-border transition-colors last:border-0", className)} {...props} />;
}

// Column header cell.
export function TableHead({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th scope="col" className={cn("px-4 py-2.5 text-xs font-medium text-muted", className)} {...props} />;
}

// Body cell.
export function TableCell({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-4 py-3 align-middle", className)} {...props} />;
}
