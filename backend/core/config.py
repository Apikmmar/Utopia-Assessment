import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False, interpolate=False)

PLACEHOLDER_PREFIX = "your_"
POSTGRES_SCHEMES = ("postgresql://", "postgres://")
URL_PLACEHOLDERS = ("[PROJECT-REF]", "[POOLER-HOST]", "[YOUR-PASSWORD]")

DATABASE_URL = "DATABASE_URL"
DATABASE_PASSWORD = "DATABASE_PASSWORD"

# Reads one environment variable, treating blank and untouched placeholders as absent.
def fromEnv(variableName):
    rawValue = (os.getenv(variableName) or "").strip()
    if not rawValue or rawValue.startswith(PLACEHOLDER_PREFIX):
        return None
    return rawValue

# Returns one setting, or the default when it is not configured.
def setting(variableName, default=None):
    return fromEnv(variableName) or default

# Returns one setting, raising when it is missing rather than starting up half
# configured.
def requiredSetting(variableName):
    value = fromEnv(variableName)
    if value is None:
        raise RuntimeError(f"Missing required configuration: {variableName}")
    return value

# Returns which of the named settings are absent, so startup can report them all at
# once instead of one per restart.
def missingSettings(variableNames):
    return [variableName for variableName in variableNames if fromEnv(variableName) is None]

# Returns the Supabase Session pooler connection URI, refusing a template or non-PostgreSQL value.
def databaseUrl():
    url = requiredSetting(DATABASE_URL)
    if not url.startswith(POSTGRES_SCHEMES):
        raise RuntimeError(f"Configuration {DATABASE_URL} must be a PostgreSQL connection URI.")
    if any(placeholder in url for placeholder in URL_PLACEHOLDERS):
        raise RuntimeError(f"Copy the actual Session pooler URI from Supabase Connect into {DATABASE_URL}.")
    return url

# Returns the database password exactly as written, since it may start with any character.
def databasePassword():
    password = os.getenv(DATABASE_PASSWORD) or ""
    if not password:
        raise RuntimeError(f"Missing required configuration: {DATABASE_PASSWORD}")
    return password


__all__ = [
    "databasePassword",
    "databaseUrl",
    "fromEnv",
    "missingSettings",
    "requiredSetting",
    "setting",
]
