import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False, interpolate=False)

PLACEHOLDER_PREFIX = "your_"
POSTGRES_SCHEMES = ("postgresql://", "postgres://")
URL_PLACEHOLDERS = ("[PROJECT-REF]", "[POOLER-HOST]")

DATABASE_URL = "DATABASE_URL"
DATABASE_PASSWORD = "DATABASE_PASSWORD"

AUTH_SESSION_HOURS = "AUTH_SESSION_HOURS"
AUTH_COOKIE_NAME = "AUTH_COOKIE_NAME"
AUTH_COOKIE_SECURE = "AUTH_COOKIE_SECURE"
APP_ALLOWED_ORIGIN = "APP_ALLOWED_ORIGIN"
AUTH_ARGON2_MEMORY_KIB = "AUTH_ARGON2_MEMORY_KIB"
AUTH_ARGON2_ITERATIONS = "AUTH_ARGON2_ITERATIONS"

REQUIRED_APP_SETTINGS = (DATABASE_URL, DATABASE_PASSWORD)
DEFAULT_ALLOWED_ORIGIN = "http://localhost:5173"

TRUE_VALUES = ("1", "true", "yes", "on")
FALSE_VALUES = ("0", "false", "no", "off")

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

# Returns one positive integer setting, raising when the value is not a positive integer.
def positiveIntSetting(variableName, default):
    rawValue = fromEnv(variableName)
    if rawValue is None:
        return default
    if not rawValue.isdecimal() or int(rawValue) < 1:
        raise RuntimeError(f"Configuration {variableName} must be a positive integer.")
    return int(rawValue)

# Returns one boolean setting, raising when the value is neither a true nor a false word.
def boolSetting(variableName, default):
    rawValue = fromEnv(variableName)
    if rawValue is None:
        return default
    lowered = rawValue.lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    raise RuntimeError(f"Configuration {variableName} must be true or false.")

# Returns the absolute session lifetime in hours.
def authSessionHours():
    return positiveIntSetting(AUTH_SESSION_HOURS, 12)

# Returns the session cookie name.
def authCookieName():
    return setting(AUTH_COOKIE_NAME, "utopia_session")

# Returns whether the session cookie carries the Secure attribute; only local HTTP should disable it.
def authCookieSecure():
    return boolSetting(AUTH_COOKIE_SECURE, True)

# Returns the frontend origin allowed for CORS and the origin check; defaults to the local Vite dev server.
def allowedOrigin():
    return setting(APP_ALLOWED_ORIGIN, DEFAULT_ALLOWED_ORIGIN).rstrip("/")

# Returns the Argon2 memory cost in KiB.
def authArgon2MemoryKib():
    return positiveIntSetting(AUTH_ARGON2_MEMORY_KIB, 19456)

# Returns the Argon2 iteration count.
def authArgon2Iterations():
    return positiveIntSetting(AUTH_ARGON2_ITERATIONS, 2)

# Raises one error naming every missing required setting so startup reports them together.
def requireStartupSettings():
    missing = missingSettings(REQUIRED_APP_SETTINGS)
    if missing:
        raise RuntimeError("Missing required configuration: " + ", ".join(missing))


__all__ = [
    "allowedOrigin",
    "authArgon2Iterations",
    "authArgon2MemoryKib",
    "authCookieName",
    "authCookieSecure",
    "authSessionHours",
    "boolSetting",
    "databasePassword",
    "databaseUrl",
    "fromEnv",
    "missingSettings",
    "positiveIntSetting",
    "requireStartupSettings",
    "requiredSetting",
    "setting",
]
