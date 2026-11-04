import sys
from pathlib import Path

BACKEND_DIRECTORY = str(Path(__file__).resolve().parents[1] / "backend")
if BACKEND_DIRECTORY not in sys.path:
    sys.path.insert(0, BACKEND_DIRECTORY)

from core.auth import ROLE_ADMIN, ROLE_MANAGER, ROLE_TECHNICIAN
from core.crypto import hashPassword
from core.db import DatabaseError, transaction
from modules.user import repository as userRepository

MOCK_PASSWORD = "P@ssword123"
SEED_ACTOR = "seed_user"
EXIT_OK = 0
EXIT_FAILED = 1
SEED_USERS = (
    {"name": "Admin", "email": "admin@utopia.com", "phone": None, "roleCode": ROLE_ADMIN},
    {"name": "Manager", "email": "manager@utopia.com", "phone": None, "roleCode": ROLE_MANAGER},
    {"name": "Ali", "email": "ali@utopia.com", "phone": "60123456781", "roleCode": ROLE_TECHNICIAN},
    {"name": "Bala", "email": "bala@utopia.com", "phone": "60123456782", "roleCode": ROLE_TECHNICIAN},
)


class SeedError(Exception):
    pass


# Inserts every mock user that does not exist yet and returns the emails created and skipped.
def seedUsers(conn, users=SEED_USERS, password=MOCK_PASSWORD):
    passwordHash = hashPassword(password)
    created, skipped = [], []
    for user in users:
        role = userRepository.findActiveRole(user["roleCode"], conn=conn)
        if role is None:
            raise SeedError(f"Role {user['roleCode']} is missing or inactive; apply the migrations first.")
        values = {
            "name": user["name"], "email": user["email"], "phone": user["phone"], "role_id": role["role_id"],
            "password_hash": passwordHash, "created_by": SEED_ACTOR, "updated_by": SEED_ACTOR,
        }
        _, conflict = userRepository.insertUser(values, conn=conn)
        (skipped if conflict else created).append(user["email"])
    return created, skipped

# Seeds the mock users from the command line and returns the process exit code.
def main():
    try:
        with transaction() as conn:
            created, skipped = seedUsers(conn)
    except SeedError as error:
        print(f"Error: {error}", file=sys.stderr)
        return EXIT_FAILED
    except (DatabaseError, RuntimeError) as error:
        print(f"Error: could not reach the database ({type(error).__name__}).", file=sys.stderr)
        return EXIT_FAILED
    for email in created:
        print(f"Created {email}")
    for email in skipped:
        print(f"Skipped {email} (already exists)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

__all__ = ["MOCK_PASSWORD", "SEED_USERS", "SeedError", "main", "seedUsers"]
