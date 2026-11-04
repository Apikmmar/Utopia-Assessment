from core import db as coreDb
from core.pagination import pageOffset


class FakeCursor:
    # Keeps the shared statement log.
    def __init__(self, log):
        self.log = log

    # Records one statement and its parameters.
    def execute(self, statement, params=None):
        self.log.append((statement, params))

    # Enters the cursor context.
    def __enter__(self):
        return self

    # Leaves the cursor context without swallowing errors.
    def __exit__(self, *exc):
        return False


class FakeConnection:
    # Starts outside autocommit with an empty statement log.
    def __init__(self):
        self.autocommit = False
        self.log = []
        self.autocommitDuringStatements = None

    # Returns a cursor that records statements, noting the autocommit state they ran under.
    def cursor(self):
        self.autocommitDuringStatements = self.autocommit
        return FakeCursor(self.log)

# A search term's LIKE wildcards and escape character match literally.
def testContainsPatternEscapesWildcards():
    assert coreDb.containsPattern("50%_a\\b") == "%50\\%\\_a\\\\b%"
    assert coreDb.containsPattern("plain") == "%plain%"

# Every new connection gets the statement and lock timeouts set outside a transaction.
def testSessionTimeoutsAppliedOnConnect():
    connection = FakeConnection()
    coreDb.applySessionTimeouts(connection, None)
    assert connection.log == [
        ("SELECT set_config('statement_timeout', %s, false)", (str(coreDb.STATEMENT_TIMEOUT_MS),)),
        ("SELECT set_config('lock_timeout', %s, false)", (str(coreDb.LOCK_TIMEOUT_MS),)),
    ]
    assert connection.autocommitDuringStatements is True
    assert connection.autocommit is False

# Page numbers start at one and map to row offsets of whole pages.
def testPageOffset():
    assert pageOffset(1, 20) == 0
    assert pageOffset(3, 25) == 50

# A plain postgres URL is moved onto the psycopg driver and other URLs are left alone.
def testPsycopgUrl():
    assert coreDb.psycopgUrl("postgresql://h/db") == "postgresql+psycopg://h/db"
    assert coreDb.psycopgUrl("postgres://h/db") == "postgresql+psycopg://h/db"
    assert coreDb.psycopgUrl("sqlite://") == "sqlite://"
