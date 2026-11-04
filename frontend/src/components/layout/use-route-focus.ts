import { useEffect, useRef } from "react";
import { useLocation } from "react-router";

// Moves focus to the main region after each route change so keyboard and screen reader users land on new content.
export function useRouteFocus() {
  const ref = useRef<HTMLElement>(null);
  const { pathname } = useLocation();
  useEffect(() => {
    ref.current?.focus();
  }, [pathname]);
  return ref;
}
