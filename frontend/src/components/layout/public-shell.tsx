import type { ReactNode } from "react";
import { useRouteFocus } from "./use-route-focus";

// Centered layout for the public login and reset pages.
export function PublicShell({ children }: { children: ReactNode }) {
  const mainRef = useRouteFocus();
  return (
    <main ref={mainRef} tabIndex={-1} className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center gap-4 px-4 py-8 outline-none">
      {children}
    </main>
  );
}
