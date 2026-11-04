import { useState } from "react";
import { BrowserRouter } from "react-router";
import { AppProviders, createQueryClient } from "./providers";
import { AppRoutes } from "./routes";

// Application root: router, providers, and routes.
export function App() {
  const [queryClient] = useState(createQueryClient);
  return (
    <BrowserRouter>
      <AppProviders queryClient={queryClient}>
        <AppRoutes />
      </AppProviders>
    </BrowserRouter>
  );
}
