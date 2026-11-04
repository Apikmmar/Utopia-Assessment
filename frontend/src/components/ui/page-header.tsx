import type { ReactNode } from "react";

type PageHeaderProps = { id: string; title: string; description?: string; actions?: ReactNode };

// Page title with an optional one-line description and right-aligned actions.
export function PageHeader({ id, title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-col gap-1">
        <h1 id={id} className="text-2xl font-semibold tracking-tight">
          {title}
        </h1>
        {description ? <p className="text-sm text-muted">{description}</p> : null}
      </div>
      {actions}
    </div>
  );
}
