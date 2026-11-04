import type { ReactNode } from "react";
import { BrandMark } from "@/components/ui/brand-mark";
import { useRouteFocus } from "./use-route-focus";

// Centered layout for the public login and reset pages.
export function PublicShell({ children }: { children: ReactNode }) {
  const mainRef = useRouteFocus();
  return (
    <main
      ref={mainRef}
      tabIndex={-1}
      className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-6 px-4 py-12 outline-none"
    >
      <BrandMark className="self-center text-base" />
      {children}
    </main>
  );
}
