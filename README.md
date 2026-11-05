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
