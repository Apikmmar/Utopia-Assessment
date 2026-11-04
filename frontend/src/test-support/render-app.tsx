import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { AppProviders, createQueryClient } from "@/app/providers";
import { AppRoutes } from "@/app/routes";

// Renders the real routes and providers at a path, against whatever fetch is stubbed.
// The returned router lets a test read the current URL and go back through history.
export function renderApp(path: string) {
  const queryClient = createQueryClient();
  const router = createMemoryRouter(
    [
      {
        path: "*",
        element: (
          <AppProviders queryClient={queryClient}>
            <AppRoutes />
          </AppProviders>
        ),
      },
    ],
    { initialEntries: [path] },
  );
  return { router, ...render(<RouterProvider router={router} />) };
}
