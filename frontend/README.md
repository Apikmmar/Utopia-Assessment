# Utopia frontend

React, TypeScript, Vite, Tailwind CSS, TanStack Query, React Hook Form and Zod.

## Commands

- `npm run dev`: dev server on port 5173. `/api/*` is proxied to `http://localhost:8000` with the `/api` prefix removed.
- `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.
- `npm run test:e2e`: Playwright journey with a mocked backend (needs `npx playwright install chromium` once).

## Deployment

The app calls the relative path `/api`, so no environment variables are needed. In `vercel.json`, the first rewrite points at the Render backend (`https://utopia-assessment.onrender.com`); change it if the backend URL changes. The second rewrite serves `index.html` for every other path so nested routes survive a refresh. Set the backend `APP_ALLOWED_ORIGIN` to the Vercel site origin.
