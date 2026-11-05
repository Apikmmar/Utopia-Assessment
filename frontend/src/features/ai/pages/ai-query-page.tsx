import { useRef, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, fieldAria } from "@/components/ui/field";
import { controlClassName } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ApiError } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import { failureMessage } from "@/lib/failure-message";
import { AiAnswerCard } from "../components/ai-answer";
import { useAskQuestion } from "../queries";
import { QUESTION_MAX_LENGTH } from "../schemas";

const EXAMPLES = [
  "What jobs did technician Ali complete last week?",
  "Which technician completed the most jobs this week?",
  "How many jobs were completed today?",
];
const GENERIC_MESSAGE = "We could not answer that question. Try again.";

// Returns the form message for a failed question; limits and unavailability keep the server's explanation.
function failure(error: unknown) {
  if (error instanceof ApiError && (error.code === "AI_USAGE_LIMIT" || error.code === "AI_UNAVAILABLE")) return error.message;
  return failureMessage(error, GENERIC_MESSAGE);
}

// Operations assistant for admins and managers: one supported question at a time, answered from database records
// and worded by AI, with the records shown beside the answer.
export function AiQueryPage() {
  const ask = useAskQuestion();
  const submitting = useRef(false);
  const [question, setQuestion] = useState("");
  const [questionError, setQuestionError] = useState<string>();
  const fieldError = questionError ?? (ask.error instanceof ApiError ? ask.error.fields.question : undefined);

  // Validates the question, then sends one request even when clicked twice; the previous answer is cleared first.
  function submit() {
    const trimmed = question.trim();
    if (!trimmed) {
      setQuestionError("Type a question or pick an example.");
      return;
    }
    if (submitting.current) return;
    submitting.current = true;
    setQuestionError(undefined);
    ask.reset();
    ask.mutate(trimmed, {
      onSettled: () => {
        submitting.current = false;
      },
    });
  }

  return (
    <section aria-labelledby="ai-title" className="flex flex-col gap-6">
      <PageHeader
        id="ai-title"
        title="AI assistant"
        description="Ask about completed jobs. Answers come from the order records, worded by AI. Times are Malaysia time; weeks run Monday to Sunday."
      />
      <Card className="p-5 sm:p-6">
        <form
          aria-label="Ask the AI assistant"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
          className="flex flex-col gap-4"
        >
          <Field id="ai-question" label="Question" error={fieldError} hint="Supported: the three example questions below. Change the technician's name as needed.">
            <textarea
              rows={3}
              maxLength={QUESTION_MAX_LENGTH}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              className={cn(controlClassName, "py-2")}
              {...fieldAria("ai-question", fieldError, true)}
            />
          </Field>
          <div className="flex flex-wrap gap-2" aria-label="Example questions" role="group">
            {EXAMPLES.map((example) => (
              <Button key={example} variant="outline" className="min-h-9 px-3 text-xs" onClick={() => setQuestion(example)}>
                {example}
              </Button>
            ))}
          </div>
          <Button type="submit" className="min-h-11 sm:self-start" disabled={ask.isPending}>
            {ask.isPending ? "Asking…" : "Ask"}
          </Button>
        </form>
      </Card>
      <div aria-live="polite" className="flex flex-col gap-4">
        {ask.isPending ? <p className="text-sm text-muted">Looking up the records…</p> : null}
        {ask.isError && !fieldError ? <Alert tone="error">{failure(ask.error)}</Alert> : null}
        {ask.data ? <AiAnswerCard answer={ask.data} /> : null}
      </div>
    </section>
  );
}
