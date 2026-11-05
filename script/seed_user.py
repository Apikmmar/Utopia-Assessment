import argparse
import json
import sys
from pathlib import Path

BACKEND_DIRECTORY = str(Path(__file__).resolve().parents[1] / "backend")
if BACKEND_DIRECTORY not in sys.path:
    sys.path.insert(0, BACKEND_DIRECTORY)

from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from core import config
from core.crypto import hashPassword
from core.db import DatabaseError, sessionTable, transaction, userTable
from modules.user import repository as userRepository

DATA_FILE = Path(__file__).resolve().parent / "data" / "users.json"
SEED_ACTOR = "seed_user"
LEGACY_ACTORS = ("demo-seed",)
MOCK_PASSWORD = "P@ssword123"
EXIT_OK = 0
EXIT_FAILED = 1


class SeedError(Exception):
    pass


# Returns the database host from DATABASE_URL, parsed as the engine parses it, so the target can be shown without
# the user or password.
def targetHost():
    return make_url(config.databaseUrl()).host or "unknown host"

# Loads the mock user data file.
def loadData(path=DATA_FILE):
    return json.loads(path.read_text(encoding="utf-8"))

# Inserts every mock user that does not exist yet and returns the emails created and skipped.
def seedUsers(conn, data, password=MOCK_PASSWORD):
    passwordHash = hashPassword(password)
    created, skipped = [], []
    for user in data["users"]:
        role = userRepository.findActiveRole(user["role"], conn=conn)
        if role is None:
            raise SeedError(f"Role {user['role']} is missing or inactive; apply the migrations first.")
        values = {
            "name": user["name"], "email": user["email"], "phone": user["phone"], "role_id": role["role_id"],
            "password_hash": passwordHash, "created_by": SEED_ACTOR, "updated_by": SEED_ACTOR,
        }
        _, conflict = userRepository.insertUser(values, conn=conn)
        (skipped if conflict else created).append(user["email"])
    return created, skipped

# Deletes every seeded user, including those older seed versions created, with their sessions; a user that orders,
# events, or files still name is kept. Returns the emails removed and kept.
def removeUsers(conn):
    rows = conn.execute(
        select(userTable.c.user_id, userTable.c.email).where(userTable.c.created_by.in_((SEED_ACTOR, *LEGACY_ACTORS))).order_by(userTable.c.email)
    ).all()
    removed, kept = [], []
    for row in rows:
        try:
            with conn.begin_nested():
                conn.execute(delete(sessionTable).where(sessionTable.c.user_id == row.user_id))
                conn.execute(delete(userTable).where(userTable.c.user_id == row.user_id))
            removed.append(row.email)
        except IntegrityError:
            kept.append(row.email)
    return removed, kept

# Seeds or removes the mock users from the command line and returns the process exit code.
def main(argv=None):
    parser = argparse.ArgumentParser(description="Load the mock users from script/data/users.json.")
    parser.add_argument("--yes", action="store_true", help="Confirm writing to the database named by DATABASE_URL.")
    parser.add_argument("--remove", action="store_true", help="Delete the seeded users instead of creating them.")
    args = parser.parse_args(argv)
    try:
        print(f"Target database host: {targetHost()}")
        if not args.yes:
            print("Nothing written. Run again with --yes to confirm this is a development database.", file=sys.stderr)
            return EXIT_FAILED
        with transaction() as conn:
            done, other = removeUsers(conn) if args.remove else seedUsers(conn, loadData())
    except SeedError as error:
        print(f"Error: {error}", file=sys.stderr)
        return EXIT_FAILED
    except (DatabaseError, RuntimeError) as error:
        print(f"Error: could not write the mock users ({type(error).__name__}).", file=sys.stderr)
        return EXIT_FAILED
    for email in done:
        print(f"{'Removed' if args.remove else 'Created'} {email}")
    for email in other:
        print(f"Kept {email} (orders still name this user; run seed_demo_orders.py --remove first)" if args.remove else f"Skipped {email} (already exists)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

__all__ = ["MOCK_PASSWORD", "SEED_ACTOR", "SeedError", "loadData", "main", "removeUsers", "seedUsers"]
