import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { useNavigate } from "react-router";
import { authKeys } from "@/features/auth/queries";
import { setUnauthorizedHandler } from "@/lib/api-client";
import { QUERY_STALE_TIME_MS, queryRetryDelay, shouldRetryQuery } from "@/lib/query-retry";

// Creates the shared query client: queries retry only transient failures, mutations never retry.
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetryQuery, retryDelay: (failureCount) => queryRetryDelay(failureCount), staleTime: QUERY_STALE_TIME_MS, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}

// Clears the session cache and routes to /login whenever a protected call answers 401.
function UnauthorizedBridge() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  useEffect(() => {
    setUnauthorizedHandler(() => {
      queryClient.clear();
      queryClient.setQueryData(authKeys.me(), null);
      navigate("/login", { replace: true });
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient, navigate]);
  return null;
}

type AppProvidersProps = { queryClient: QueryClient; children: ReactNode };

// Supplies server-state caching and the global 401 handling; must sit inside a router.
export function AppProviders({ queryClient, children }: AppProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <UnauthorizedBridge />
      {children}
    </QueryClientProvider>
  );
}
