import sys
from pathlib import Path

BACKEND_DIRECTORY = str(Path(__file__).resolve().parents[1] / "backend")
if BACKEND_DIRECTORY not in sys.path:
    sys.path.insert(0, BACKEND_DIRECTORY)

from core import config
from core.storage import StorageUnavailable, closeStorage, getStorage
from modules.attachment.constants import BUCKET_ALLOWED_TYPES, BUCKET_FILE_SIZE_LIMIT

EXIT_OK = 0
EXIT_FAILED = 1

# Creates or updates the private order files bucket with its size limit and allowed types; safe to re-run.
def setupStorage(storage=None):
    client = storage or getStorage()
    return client.ensureBucket(BUCKET_FILE_SIZE_LIMIT, BUCKET_ALLOWED_TYPES)

# Runs the bucket setup and prints the outcome without any URL or key.
def main():
    try:
        outcome = setupStorage()
    except StorageUnavailable as error:
        print(f"Storage setup failed: {error.reason}. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env.")
        return EXIT_FAILED
    finally:
        closeStorage()
    print(f"Bucket {config.storageBucket()} {outcome}: private, {BUCKET_FILE_SIZE_LIMIT // (1024 * 1024)} MB limit, {len(BUCKET_ALLOWED_TYPES)} allowed types.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
