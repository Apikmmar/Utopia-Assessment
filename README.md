# Utopia: Sejuk Sejuk Service Operations System

An internal operations system for Sejuk Sejuk Service Sdn Bhd that covers the service workflow from order to review:

```text
Admin creates an order -> Technician receives the job -> Technician completes the service
-> System prepares the WhatsApp notification -> Manager reviews the job -> KPI dashboard updates
```

- Live demo: https://utopia-assessment-two.vercel.app
- API: https://utopia-assessment.onrender.com (free plan; the first request after 15 idle minutes can take up to a minute)

### Demo accounts

All accounts use the password `P@ssword123`.

| Role | Email |
| --- | --- |
| Admin | `admin@utopia.com` |
| Manager | `manager@utopia.com` |
| Technician | `ali@utopia.com`, `bala@utopia.com`, `chong@utopia.com` |

## What I built

| Module | Status | What it does |
| --- | --- | --- |
| Module 1: Admin Portal, Order Submission | Done, with both bonuses | Admin form with every listed field: Order No (auto-generated as `ORD-000001`), customer name, phone, address, problem description, service type dropdown, quoted price, assigned technician, and admin notes. After saving, the admin sees an order summary and a WhatsApp link that sends the job to the technician. Admins can edit or reassign an order until work starts. |
| Module 2: Technician Portal, Service Job | Done, with the payment bonus and the customer feedback bonus | Mobile-first "My jobs" page. The technician starts the job, then records the completion: order ID (read-only), work done, extra charges, up to 6 photos, videos, or PDFs, final amount (calculated as quoted price plus extra charges), remarks, technician name, and timestamp. Optional payment received: amount, method (cash, card, bank transfer, e-wallet), and a receipt photo. Technicians can also postpone a visit with a reason and a new date. |
| Module 3: WhatsApp Notification Trigger | Done | When an order reaches Job Done, the system creates the customer feedback message from the assessment template and a `wa.me` deep link with the message pre-filled. Assigning a technician creates a job message for the technician in the same way. Every notification is stored, and a Notifications page shows which are pending and which were sent. |
| Bonus: KPI Dashboard | Done (weekly) | Admins and managers see the weekly figures per technician: jobs completed, total amount, and postponements. The page has summary cards, a ranked leaderboard, a bar chart, and week navigation. |
| Manager review | Done | A review queue for managers. They review Job Done orders, then close them. |
| Authentication | Done (bonus) | Real login with email and password instead of a role switch. Admins create and edit users and set passwords. |
| AI Module: Operations Query Window | Not built | The database already has the tables for it (`llm_model`, `llm_invocation`, `token_usage`, `setting`). The design is described under [How AI was integrated](#how-ai-was-integrated). |
| Optional advanced AI challenges | Not built | |

The status flow is `New -> Assigned -> In Progress -> Job Done -> Reviewed -> Closed`, and the backend enforces it:

- Only an admin creates orders and assigns technicians.
- Only the assigned technician can start, postpone, and complete a job.
- Only a manager can review and close.
- Every key action is written to an `order_event` history with the actor, the time, and the request ID, so every order is traceable.

## Tech stack

| Layer | Used | Note |
| --- | --- | --- |
| Front-end | React 19, TypeScript, Vite, React Router, TanStack Query, React Hook Form, Zod | Preferred stack |
| Styling | Tailwind CSS 4 | Preferred stack |
| Backend | Python, FastAPI, SQLAlchemy Core, psycopg | Supabase is used for data only; the API is a separate service so business rules and access control stay on the server |
| Database | Supabase PostgreSQL | Preferred stack. Versioned SQL migrations in `db/migrations/` |
| File storage | Supabase Storage (private bucket, signed URLs) | Preferred stack |
| Deployment | Vercel (frontend), Render (backend) | Vercel proxies `/api/*` to Render |
| Login | Email and password, Argon2id hashing, server-side session in an HttpOnly cookie | Basic authentication bonus |
| Tests | pytest (unit, API, and PostgreSQL tests), Vitest, Testing Library, Playwright | |

## Architecture decisions

- **Modular monolith.** One FastAPI service with flat feature modules (`auth`, `user`, `order`, `service_type`, `attachment`, `completion`, `notification`, `kpi`) on a shared `core/`. Dependencies go one way, and only the `order` module changes an order's status. This is the smallest design that keeps business rules separate and testable; there is no need for separate services at this size.
- **Status machine as data.** Allowed transitions and the role allowed for each are one table in `modules/order/constants.py`. Each transition is one guarded `UPDATE ... WHERE status = :from`, so two people acting at once cannot both succeed; the loser gets `409`.
- **Traceability.** Every action writes an `order_event` row in the same transaction as the change. The KPI postponement count is read from these events.
- **Files go straight to storage.** The API issues a signed upload URL, the phone uploads directly to Supabase Storage, and the API checks each file's size and type before it accepts the completion. Large videos never pass through the API server.
- **Notifications prepared in the request.** The notification row, message, and WhatsApp link are created in the same transaction as the status change, so the response already carries the link and nothing is lost if a background process stops. Preparing is behind a provider interface, so a WhatsApp Business API provider can replace deep links later without touching the order flow.
- **Real sessions instead of a role switch.** An opaque token in an HttpOnly, Secure cookie maps to a server-side session, so logout and role changes take effect on the next request. State-changing requests must come from the allowed origin.
- **Same origin in production.** Vercel rewrites `/api/*` to Render, so the browser only talks to the Vercel domain and the session cookie stays first-party.
- **KPI as a read-only module.** It turns a Monday to Sunday week in Malaysia time into UTC bounds and runs two aggregate queries. It writes nothing, and no other module depends on it.

## Challenges and assumptions

Challenges:

- **Uploads on mobile.** Up to 6 files, videos up to 49 MB, and HEIC photos from iPhones had to fit the Supabase free plan's 50 MB per-file limit and stay reliable on mobile data. Signed direct uploads with server-side verification solved it.
- **WhatsApp without a Business API.** A `wa.me` link cannot report whether a message was actually sent, so the system records when a user opened the message in WhatsApp from the app and treats that as sent.
- **Deployment.** Render runs the API as a plain web service, so all work, including notifications, runs inside API requests.

Assumptions:

- The five service types are Aircond cleaning, Repair, Gas refill, Installation, and General servicing.
- Admin notes are job instructions for the technician. They are shown to staff only and never sent to the customer.
- Final amount = quoted price + extra charges. A payment record is optional and stored next to the completion.
- Postponing a visit records a reason and a new date and keeps the status unchanged. "Postpone / Reschedule" on the dashboard counts these events.
- Weeks run Monday to Sunday in Asia/Kuala_Lumpur time.
- The mock technicians are Ali, Bala, and Chong. Demo data covers 28 Sep to 5 Nov 2026.

## How AI was integrated

AI is not built into the running system yet. The AI Operations Query Window is the next module, and this is its design:

```text
Manager question
  -> the AI model picks one allowed query and fills its parameters (technician, period)
  -> the backend validates the parameters and runs that fixed, read-only query
  -> the AI model writes the answer only from the rows returned
```

- The model never writes SQL and never sees the whole database. It can only call a short list of backend functions, the same aggregates the KPI dashboard already uses, and only for managers and admins.
- Every call is logged in the existing `llm_invocation` and `token_usage` tables, with the model chosen from `llm_model`.

### What types of AI queries are supported

None are live yet. These are the planned query types, each backed by one fixed query:

- Jobs one technician completed in a period ("What jobs did technician Ali complete last week?")
- Ranking by jobs completed in a period ("Which technician completed the most jobs this week?")
- Count of jobs completed in a period ("How many jobs were completed today?")

### Limitations of the AI implementation

- The module is not implemented, so the portal has no AI assistant today.
- As designed, it would answer only questions that map to one of the allowed queries. Anything else gets a clear "I can't answer that yet" instead of a guess.

## Limitations

- No AI module yet (see above).
- WhatsApp uses deep links. The system cannot confirm that a message was delivered, and someone has to tap the link to send it.
- Managers and accounts are not notified when a job is done. They see it in the review queue.
- KPI covers weekly data only. There is no trend, month view, drill-down, or technician self-view.
- Orders cannot be cancelled, put on hold, or sent back from review, and cannot be edited after work starts.
- No offline mode for technicians. Uploads need a connection.
- The free Render plan sleeps when idle, so the first request after a pause is slow.
- Password reset has no email or one-time code proof of ownership.

The full backlog is in `.docs/enhancement.md`.

## Self-assessment

- **Easiest module:** Module 1, order submission. It is a standard form with validation, a generated order number, and one insert.
- **Hardest module:** Module 2, the technician completion. It needs a fast mobile flow, direct uploads with verification, an optional payment and receipt, and the Job Done notification, all as one consistent change.
- **What I would improve for production:**
  - A WhatsApp Business API provider for real sending and delivery status.
  - Cancel, hold, and send-back flows.
  - Offline completion with upload retry.
  - Rate limiting and lockout on login.
  - CI that runs the full test suite.
  - Monitoring, and a paid Render plan with no sleep.
- **How I used AI tools:**
  - Claude Code and Codex were the coding assistants. They followed the repository instructions in `AGENTS.md` and project skills for frontend, backend, database, and testing.
  - Each module went through a planning document, a design document, and a task list in `.docs/` before code.
  - Separate security, performance, and code-quality reviewer agents reviewed the changes.
  - I made the design decisions and checked the results with tests.

## Running locally

### Backend

The backend code is in `backend/` and imports as `core`, `modules`, and `api`, so `backend` must be on the import path. Run every command from the repository root. Settings come from `backend/.env`; copy `backend/.env.example` and fill it in.

```bash
pip install -r backend/requirements.txt                   # runtime and test dependencies
uvicorn api.main:app --app-dir backend --reload           # serve the API
python -m db.migration --dry-run                          # preview pending migrations
python -m db.migration                                    # apply them
python -m db.rollback --dry-run                           # preview reversing the latest one
python script/seed_user.py --yes                          # mock users from script/data/users.json: admin, manager, 3 technicians; password P@ssword123
python script/seed_demo_orders.py --yes                   # KPI demo data from script/data/demo_orders.json
python script/seed_demo_orders.py --yes --remove          # delete the demo orders again
python script/seed_user.py --yes --remove                 # delete the mock users (remove the demo orders first)
```

Both seed scripts print the target host and write nothing without `--yes`, and running one a second time adds nothing. `seed_user.py` creates one admin, one manager, and three technicians (Ali, Bala, Chong) from `script/data/users.json`. `seed_demo_orders.py` needs those users and migration `0016` first, and it creates no users of its own. It loads about five weeks of orders (28 Sep to 5 Nov 2026, Kuala Lumpur time) with completions and postponements, and marks every order `created_by = 'demo-seed'`. `seed_user.py --remove` keeps any user that orders still name, so remove the demo orders first.

### Frontend

```bash
cd frontend
npm ci
npm run dev      # http://localhost:5173, proxies /api to the local backend
npm test
npm run lint
```

### Tests

`pytest.ini` sets `pythonpath = backend .` and `testpaths = tests`. Markers come from the folder a test lives in: `tests/unit` (`unit`), `tests/integration` (`integration`), and `tests/db` (`db`).

```bash
python -m pytest -m unit -q          # no database needed
RUN_DB_TESTS=1 python -m pytest -q   # everything, including PostgreSQL-backed checks
```

Database tests are skipped unless `RUN_DB_TESTS=1`.

- They connect with `TEST_DATABASE_URL` and `TEST_DATABASE_PASSWORD`, or with `DATABASE_URL` and `DATABASE_PASSWORD` from `backend/.env` when those are unset.
- Each test creates its own `utopia_test_<id>` schema, applies the repository migrations into it, points the application engine at it through `search_path`, and drops it afterwards, so nothing is written to `public`.
- The database role needs permission to create schemas.
- Against a remote database each test takes a few seconds. Run one test process at a time.

## Deploy

The backend runs on Render as one web service, defined in `render.yaml`. The frontend runs on Vercel from `frontend/`, and `frontend/vercel.json` proxies `/api/*` to the Render service.

### Backend on Render

1. In Render, choose New > Blueprint and select this repository. Render reads `render.yaml`, builds from the repository root, and `--app-dir backend` puts the backend on the import path.
2. Fill in the secret settings it asks for:
   - `DATABASE_URL`: the Supabase Session pooler URI.
   - `DATABASE_PASSWORD`: the database password.
   - `APP_ALLOWED_ORIGIN`: the Vercel production URL with no trailing slash.
   - `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`: needed for order file uploads.
3. Deploy. Render checks `/info` for liveness. Open `/health` to confirm the database connection.

Apply migrations from your machine before the first deploy and whenever `db/migrations/` changes. Point `backend/.env` at the production database, then run:

```bash
python -m db.migration --dry-run   # check what will run
python -m db.migration
```

The seed scripts create users with a known password. Run them only on a demo database.

### Frontend on Vercel

1. Import the repository in Vercel and set Root Directory to `frontend`. `vercel.json` sets the Vite build, the `dist` output, and the rewrites.
2. The backend runs at `https://utopia-assessment.onrender.com`. If its URL changes, update the `/api` rewrite in `frontend/vercel.json`.
3. Set `APP_ALLOWED_ORIGIN` on Render to the exact Vercel production URL.

State-changing requests are accepted only from `APP_ALLOWED_ORIGIN`, so Vercel preview URLs can read data but cannot log in or save.
