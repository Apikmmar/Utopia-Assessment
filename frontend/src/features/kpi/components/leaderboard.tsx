import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMyr } from "@/features/orders/money";
import { cn } from "@/lib/cn";
import type { LeaderboardRow } from "../schemas";

const PODIUM_RANK = 3;

// Returns the rank text with a "tied" note when another row shares it, so ties never rely on position alone.
function rankText(row: LeaderboardRow, rows: LeaderboardRow[]) {
  const tied = rows.filter((other) => other.rank === row.rank).length > 1;
  return tied ? `${row.rank} (tied)` : String(row.rank);
}

// Technicians ranked by the server: a table on wide screens and a card list on phones. The top three are bold.
export function Leaderboard({ rows }: { rows: LeaderboardRow[] }) {
  return (
    <>
      <div className="hidden sm:block">
        <Table aria-label="Technician leaderboard">
          <TableHeader>
            <TableRow>
              <TableHead className="w-24">Rank</TableHead>
              <TableHead>Technician</TableHead>
              <TableHead className="text-right">Jobs completed</TableHead>
              <TableHead className="text-right">Total amount</TableHead>
              <TableHead className="text-right">Postponed</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.technician.userId} className={cn(row.rank <= PODIUM_RANK && row.jobsCompleted > 0 && "font-semibold")}>
                <TableCell className="tabular-nums">{rankText(row, rows)}</TableCell>
                <TableCell>{row.technician.name}</TableCell>
                <TableCell className="text-right tabular-nums">{row.jobsCompleted}</TableCell>
                <TableCell className="text-right tabular-nums">{formatMyr(row.totalAmount)}</TableCell>
                <TableCell className="text-right tabular-nums">{row.postponed}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <ol aria-label="Technician leaderboard" className="flex flex-col gap-3 sm:hidden">
        {rows.map((row) => (
          <li key={row.technician.userId} className="rounded-xl border border-border bg-card p-4 shadow-xs">
            <p className={cn("text-sm", row.rank <= PODIUM_RANK && row.jobsCompleted > 0 && "font-semibold")}>
              #{rankText(row, rows)} {row.technician.name}
            </p>
            <dl className="mt-2 grid grid-cols-3 gap-2 text-sm">
              <div>
                <dt className="text-xs text-muted">Jobs</dt>
                <dd className="tabular-nums">{row.jobsCompleted}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Amount</dt>
                <dd className="tabular-nums">{formatMyr(row.totalAmount)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Postponed</dt>
                <dd className="tabular-nums">{row.postponed}</dd>
              </div>
            </dl>
          </li>
        ))}
      </ol>
    </>
  );
}
