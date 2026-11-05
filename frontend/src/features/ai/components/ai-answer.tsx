import { Card } from "@/components/ui/card";
import { TextLink } from "@/components/ui/text-link";
import { formatDateTime } from "@/features/orders/notifications";
import type { AiAnswer, AiResult } from "../schemas";

// Lists the database records behind an answer: the jobs with order links, the leaders, or the count.
function Facts({ result }: { result: AiResult }) {
  if (result.kind === "completed_count") {
    return (
      <p className="text-sm">
        Jobs completed: <strong>{result.total}</strong>
      </p>
    );
  }
  if (result.kind === "top_technician") {
    if (result.total === 0) return <p className="text-sm text-muted">No completed jobs in this period.</p>;
    return (
      <div className="flex flex-col gap-2 text-sm">
        <p>
          Most jobs: <strong>{result.jobsCompleted}</strong>
          {result.total > 1 ? ` (${result.total} technicians tied)` : ""}
        </p>
        <ul className="list-disc pl-5">
          {result.items.map((item) => (
            <li key={item.userId}>{item.name}</li>
          ))}
        </ul>
        {result.truncated ? <p className="text-muted">Showing {result.items.length} of {result.total}.</p> : null}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2 text-sm">
      <p>
        {result.technician.name}: <strong>{result.total}</strong> {result.total === 1 ? "job" : "jobs"}
      </p>
      {result.items.length > 0 ? (
        <ul className="flex flex-col divide-y divide-border rounded-lg border border-border">
          {result.items.map((item) => (
            <li key={item.orderId} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-3 py-2">
              <TextLink to={`/orders/${item.orderId}`}>{item.orderNo}</TextLink>
              <span>{item.serviceType}</span>
              <span className="text-muted">{formatDateTime(item.completedAt)}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {result.truncated ? <p className="text-muted">Showing the first {result.items.length} of {result.total}.</p> : null}
    </div>
  );
}

// One answer: the summary as plain text, where it came from, the period, and the database facts.
export function AiAnswerCard({ answer }: { answer: AiAnswer }) {
  return (
    <Card className="flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="ai-answer-title">
      <div className="flex flex-col gap-1">
        <h2 id="ai-answer-title" className="text-base font-semibold">
          Answer
        </h2>
        {answer.period ? <p className="text-xs text-muted">Period: {answer.period.label}</p> : null}
      </div>
      <p className="whitespace-pre-line text-sm">{answer.answer}</p>
      {answer.notice ? <p className="text-sm text-muted">{answer.notice}</p> : null}
      {answer.summarySource ? (
        <p className="text-xs text-muted">{answer.summarySource === "ai" ? "Worded by AI from the records below." : "Written from the records below."}</p>
      ) : null}
      {answer.result ? (
        <div className="flex flex-col gap-2 border-t border-border pt-4">
          <h3 className="text-sm font-semibold">Database records</h3>
          <Facts result={answer.result} />
        </div>
      ) : null}
    </Card>
  );
}
