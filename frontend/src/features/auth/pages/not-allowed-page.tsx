import { Link } from "react-router";
import { Button } from "@/components/ui/button";

// Page shown when the signed-in role may not use the requested screen.
export function NotAllowedPage() {
  return (
    <section aria-labelledby="not-allowed-title" className="mx-auto flex max-w-md flex-col items-center gap-3 py-16 text-center">
      <p className="text-sm font-medium text-muted">403</p>
      <h1 id="not-allowed-title" className="text-2xl font-semibold tracking-tight">
        Not allowed
      </h1>
      <p className="text-sm text-muted">Your role does not have access to this page.</p>
      <Button asChild variant="outline" className="mt-3">
        <Link to="/">Go to your home page</Link>
      </Button>
    </section>
  );
}
