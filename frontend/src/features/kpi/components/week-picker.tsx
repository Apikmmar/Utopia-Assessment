import { Button } from "@/components/ui/button";
import type { Dashboard } from "../schemas";
import { shiftWeek } from "../week";

type WeekPickerProps = { week: Dashboard["week"]; onChange: (date: string | undefined) => void };

// Shows the week being viewed with previous, this week, and next controls; next stops at the current week.
export function WeekPicker({ week, onChange }: WeekPickerProps) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Week">
      <Button variant="outline" className="min-h-11" onClick={() => onChange(shiftWeek(week.startDate, -1))}>
        ← Previous
      </Button>
      <p className="min-w-40 px-2 text-center text-sm font-medium" aria-live="polite">
        {week.label}
      </p>
      <Button variant="outline" className="min-h-11" disabled={week.isCurrent} onClick={() => onChange(shiftWeek(week.startDate, 1))}>
        Next →
      </Button>
      {week.isCurrent ? null : (
        <Button variant="ghost" className="min-h-11" onClick={() => onChange(undefined)}>
          This week
        </Button>
      )}
    </div>
  );
}
