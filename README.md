# Utopia

## Backend

Backend code lives in `backend/` and imports as `core`, `modules`, and `api`, so `backend` must be on the import path. Run every command from the repository root. Settings come from `backend/.env`; copy `backend/.env.example` and fill it in.

```bash
pip install -r backend/requirements.txt                   # runtime and test dependencies
cd backend && uvicorn api.main:app --reload            # serve the API (or: uvicorn api.main:app --app-dir backend from the root)
python -m db.migration --dry-run                          # preview pending migrations
python -m db.migration                                    # apply them
python -m db.rollback --dry-run                           # preview reversing the latest one
python script/seed_user.py                                # mock users: admin, manager, 2 technicians; password P@ssword123
python script/seed_demo_orders.py --yes                   # KPI demo data from script/data/demo_orders.json (development only)
python script/seed_demo_orders.py --yes --remove          # delete the demo orders again
```

`seed_demo_orders.py` needs `seed_user.py` and migration `0016` first. It loads about five weeks of orders (28 Sep to 5 Nov 2026, Kuala Lumpur time) with completions and postponements, adds the technicians Chong and Devi with the mock password, and marks every order `created_by = 'demo-seed'`. A second run adds nothing. Without `--yes` it only prints the target host.

## Tests

`pytest.ini` sets `pythonpath = backend .` and `testpaths = tests`. Markers are applied from the folder a test lives in: `tests/unit` (`unit`), `tests/integration` (`integration`), and `tests/db` (`db`).

```bash
python -m pytest -m unit -q          # no database needed
RUN_DB_TESTS=1 python -m pytest -q   # everything, including PostgreSQL-backed checks
```

Database tests are skipped unless `RUN_DB_TESTS=1`. They connect with `TEST_DATABASE_URL` and `TEST_DATABASE_PASSWORD`, or with `DATABASE_URL` and `DATABASE_PASSWORD` from `backend/.env` when those are unset. Each test creates its own `utopia_test_<id>` schema, applies the repository migrations into it, points the application engine at it through `search_path`, and drops it afterwards, so nothing is written to `public`. The database role needs permission to create schemas. Against a remote database each test takes a few seconds; run one test process at a time.

## Deploy

The backend runs on Render as one web service, defined in `render.yaml`. The frontend runs on Vercel from `frontend/`, and `frontend/vercel.json` proxies `/api/*` to the Render service. The browser then talks to a single origin, so the session cookie stays first-party.

### Backend on Render

1. In Render, choose New > Blueprint and select this repository. Render reads `render.yaml` and creates the `utopia-api` web service in Singapore. It builds and starts from the repository root, and `--app-dir backend` puts the backend on the import path.
2. Fill in the secret settings it asks for:
   - `DATABASE_URL`: the Supabase Session pooler URI.
   - `DATABASE_PASSWORD`: the database password.
   - `APP_ALLOWED_ORIGIN`: the Vercel production URL, for example `https://utopia.vercel.app`, with no trailing slash.
   - `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`: needed for order file uploads.
3. Deploy. Render checks `/info` for liveness; open `https://<service>.onrender.com/health` to confirm the database connection.

Apply migrations from your machine before the first deploy and whenever `db/migrations/` changes. Point `backend/.env` at the production database, then run:

```bash
python -m db.migration --dry-run   # check what will run
python -m db.migration
```

Do not run `script/seed_user.py` or `script/seed_demo_orders.py` against production: they create users with a known password and demo data.

### Frontend on Vercel

1. Import the repository in Vercel and set Root Directory to `frontend`. `vercel.json` sets the Vite build, the `dist` output, and the rewrites.
2. The backend runs at `https://utopia-assessment.onrender.com`; if Render ever gives it another URL, update the `/api` rewrite destination in `frontend/vercel.json`.
3. Deploy, then set `APP_ALLOWED_ORIGIN` on Render to the exact Vercel production URL.

Notes:
- State-changing requests are accepted only from `APP_ALLOWED_ORIGIN`. Vercel preview URLs can read data but cannot log in or save.
- On the Render free plan the service sleeps after about 15 minutes without traffic. The first request after that takes up to a minute.
