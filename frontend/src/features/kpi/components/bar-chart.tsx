import { useId } from "react";
import type { LeaderboardRow } from "../schemas";

// Returns the one-line summary a screen reader hears before the data table.
export function chartSummary(rows: LeaderboardRow[]) {
  const top = rows[0];
  if (!top || top.jobsCompleted === 0) return "No technician completed a job this week.";
  const leaders = rows.filter((row) => row.jobsCompleted === top.jobsCompleted).map((row) => row.technician.name);
  return `${leaders.join(" and ")} completed the most jobs: ${top.jobsCompleted}.`;
}

// Horizontal bars of jobs completed per technician in leaderboard order, one hue, values labelled at the bar end,
// with a visually hidden table holding the same numbers.
export function JobsBarChart({ rows }: { rows: LeaderboardRow[] }) {
  const summaryId = useId();
  const max = Math.max(1, ...rows.map((row) => row.jobsCompleted));
  return (
    <figure aria-describedby={summaryId} className="flex flex-col gap-3">
      <figcaption className="text-base font-semibold">Jobs completed per technician</figcaption>
      <p id={summaryId} className="text-sm text-muted">
        {chartSummary(rows)}
      </p>
      <div aria-hidden="true" className="flex flex-col gap-2" data-testid="jobs-bar-chart">
        {rows.map((row) => (
          <div key={row.technician.userId} className="grid grid-cols-[minmax(0,7rem)_1fr_2.5rem] items-center gap-3 text-sm sm:grid-cols-[minmax(0,10rem)_1fr_3rem]">
            <span className="truncate" title={row.technician.name}>
              {row.technician.name}
            </span>
            <div className="h-5 rounded-r bg-subtle" title={`${row.technician.name}: ${row.jobsCompleted} jobs`}>
              {row.jobsCompleted > 0 ? (
                <div className="h-full rounded-r bg-chart" style={{ width: `${(row.jobsCompleted / max) * 100}%` }} />
              ) : null}
            </div>
            <span className="text-right tabular-nums">{row.jobsCompleted}</span>
          </div>
        ))}
      </div>
      <table className="sr-only">
        <caption>Jobs completed per technician</caption>
        <thead>
          <tr>
            <th scope="col">Technician</th>
            <th scope="col">Jobs completed</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.technician.userId}>
              <th scope="row">{row.technician.name}</th>
              <td>{row.jobsCompleted}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
