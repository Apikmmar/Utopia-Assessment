import { Link } from "react-router";

// Page shown when the signed-in role may not use the requested screen.
export function NotAllowedPage() {
  return (
    <section aria-labelledby="not-allowed-title" className="flex flex-col gap-3">
      <h1 id="not-allowed-title" className="text-2xl font-semibold">
        Not allowed
      </h1>
      <p>Your role does not have access to this page.</p>
      <Link to="/" className="inline-flex min-h-11 items-center text-primary underline">
        Go to your home page
      </Link>
    </section>
  );
}
