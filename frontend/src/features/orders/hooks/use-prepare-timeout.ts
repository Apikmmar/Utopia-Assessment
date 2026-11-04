import { useEffect, useState } from "react";
import { PREPARE_TIMEOUT_MS } from "../notifications";

// Returns true once a notification has stayed queued for longer than the prepare timeout; remount to reset it.
export function usePrepareTimeout(isQueued: boolean) {
  const [expired, setExpired] = useState(false);
  useEffect(() => {
    if (!isQueued) return undefined;
    const timer = setTimeout(() => setExpired(true), PREPARE_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [isQueued]);
  return isQueued && expired;
}
