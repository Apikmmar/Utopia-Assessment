from datetime import datetime, timedelta, timezone
import pytest
from argon2 import PasswordHasher
from core import crypto
from core.auth import resolveSession
from core.token import hashToken
from modules.auth import service
from tests.support import STRONG_PASSWORD

EMAIL = "auth.service.test@example.com"
NEW_PASSWORD = "a-brand-new-password"
FIXED_NOW = datetime(2031, 5, 4, 8, 30, tzinfo=timezone.utc)
CLIENT_IP = "203.0.113.5"


# Returns a clock that always answers the given instant.
def fixedClock(instant):
    return lambda: instant

# Logs in through the service and returns the result, failing the test on a refusal.
def loginNow(email=EMAIL, password=STRONG_PASSWORD, now=service.utcNow):
    result, error = service.login(email, password, CLIENT_IP, "test-agent", now)
    assert error is None, error
    return result

# Seeds one technician with a known password and returns its id.
@pytest.fixture
def userId(seedUser):
    return seedUser(EMAIL)

# Login stores last_login_at and a session expiring after the configured hours, using the injected clock.
def testLoginSuccessUsesInjectedClock(userId, appDb):
    result = loginNow(now=fixedClock(FIXED_NOW))
    assert (result.user.email, result.user.roleCode, result.user.userId) == (EMAIL, "technician", userId)
    with appDb.connect() as conn:
        lastLogin = conn.exec_driver_sql('SELECT last_login_at FROM "user" WHERE user_id = %s', (userId,)).scalar_one()
        row = conn.exec_driver_sql("SELECT expires_at, ip, user_agent, token_hash FROM session WHERE user_id = %s", (userId,)).one()
    assert lastLogin == FIXED_NOW
    assert row.expires_at == FIXED_NOW + timedelta(hours=12)
    assert (row.ip, row.user_agent) == (CLIENT_IP, "test-agent")
    assert row.token_hash == hashToken(result.token) != result.token

# An email with spaces and capitals logs in as its normalized form.
def testLoginNormalizesEmail(userId):
    assert loginNow(email="  Auth.Service.TEST@Example.com ").user.email == EMAIL

# A wrong password, an unknown email, and a user without a hash all return the same refusal and write nothing.
def testAllFailuresReturnTheSameRefusal(userId, seedUser, scalar):
    seedUser("no.hash@example.com", password=None)
    attempts = [(EMAIL, "wrong-password-value"), ("nobody@example.com", STRONG_PASSWORD), ("no.hash@example.com", STRONG_PASSWORD)]
    results = [service.login(email, password, None, None) for email, password in attempts]
    assert results == [(None, service.INVALID_CREDENTIALS)] * 3
    assert scalar("SELECT count(*) FROM session") == 0
    assert scalar('SELECT last_login_at FROM "user" WHERE user_id = :u', u=userId) is None

# A hash made with outdated cost is replaced by a current one at login.
def testLoginRehashesOutdatedHash(userId, execute, scalar):
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(STRONG_PASSWORD)
    execute('UPDATE "user" SET password_hash = :h WHERE user_id = :u', h=weak, u=userId)
    loginNow()
    stored = scalar('SELECT password_hash FROM "user" WHERE user_id = :u', u=userId)
    assert stored != weak
    assert not crypto.needsRehash(stored)
    assert crypto.verifyPassword(STRONG_PASSWORD, stored)

# Login verifies and rehashes with no pooled connection checked out.
def testLoginHoldsNoConnectionWhileHashing(userId, appDb, execute, monkeypatch):
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(STRONG_PASSWORD)
    execute('UPDATE "user" SET password_hash = :h WHERE user_id = :u', h=weak, u=userId)
    checkedOut = []
    monkeypatch.setattr(service, "verifyPassword", lambda *args: checkedOut.append(appDb.pool.checkedout()) or crypto.verifyPassword(*args))
    monkeypatch.setattr(service, "hashPassword", lambda *args: checkedOut.append(appDb.pool.checkedout()) or crypto.hashPassword(*args))
    loginNow()
    assert checkedOut == [0, 0]

# A live session resolves to its user.
def testResolveAcceptsLiveSession(userId):
    user = resolveSession(loginNow().token)
    assert (user.userId, user.email, user.roleCode) == (userId, EMAIL, "technician")

# A session whose expiry has passed does not resolve.
def testResolveRejectsExpiredSession(userId):
    token = loginNow(now=fixedClock(service.utcNow() - timedelta(hours=13))).token
    assert resolveSession(token) is None

# A logged-out session does not resolve and logging out twice is harmless.
def testResolveRejectsRevokedSessionAndLogoutIsIdempotent(userId):
    token = loginNow().token
    service.logout(token)
    service.logout(token)
    assert resolveSession(token) is None

# A modified or unknown token does not resolve.
def testResolveRejectsTamperedToken(userId):
    token = loginNow().token
    assert resolveSession(token[:-1] + ("A" if token[-1] != "A" else "B")) is None
    assert resolveSession("not-a-token") is None

# last_used_at is refreshed when older than five minutes and left alone when recent.
def testLastUsedTouchedOnlyWhenStale(userId, execute, scalar):
    token = loginNow().token
    age = "SELECT now() - last_used_at FROM session WHERE user_id = :u"
    execute("UPDATE session SET last_used_at = now() - interval '1 hour'")
    resolveSession(token)
    assert scalar(age, u=userId) < timedelta(minutes=1)
    execute("UPDATE session SET last_used_at = now() - interval '2 minutes'")
    resolveSession(token)
    assert scalar(age, u=userId) >= timedelta(minutes=2)

# A reset changes the hash and password_changed_at and revokes every session of that user only.
def testResetRevokesAllSessionsOfThatUser(userId, seedUser, appDb):
    otherId = seedUser("other.user@example.com")
    first, second = loginNow().token, loginNow().token
    otherToken = loginNow(email="other.user@example.com").token
    assert service.resetPassword("AUTH.service.test@example.com ", NEW_PASSWORD, fixedClock(FIXED_NOW)) == (True, None)
    assert resolveSession(first) is None and resolveSession(second) is None
    assert resolveSession(otherToken).userId == otherId
    with appDb.connect() as conn:
        row = conn.exec_driver_sql('SELECT password_hash, password_changed_at FROM "user" WHERE user_id = %s', (userId,)).one()
    assert crypto.verifyPassword(NEW_PASSWORD, row.password_hash)
    assert row.password_changed_at == FIXED_NOW
    assert service.login(EMAIL, STRONG_PASSWORD, None, None) == (None, service.INVALID_CREDENTIALS)
    assert loginNow(password=NEW_PASSWORD).token

# A reset for an unknown email changes no user and no session and answers the same success.
def testResetUnknownEmailChangesNothing(userId, scalar):
    token = loginNow().token
    snapshot = "SELECT md5(string_agg(coalesce(password_hash, '') || coalesce(password_changed_at::text, ''), ',' ORDER BY user_id)) FROM \"user\""
    before = scalar(snapshot)
    assert service.resetPassword("nobody@example.com", NEW_PASSWORD) == (True, None)
    assert scalar(snapshot) == before
    assert scalar("SELECT count(*) FROM session WHERE revoked_at IS NULL") == 1
    assert resolveSession(token) is not None

# A reset hashes the new password with no pooled connection checked out.
def testResetHoldsNoConnectionWhileHashing(userId, appDb, monkeypatch):
    checkedOut = []
    monkeypatch.setattr(service, "hashPassword", lambda *args: checkedOut.append(appDb.pool.checkedout()) or crypto.hashPassword(*args))
    service.resetPassword(EMAIL, NEW_PASSWORD)
    assert checkedOut == [0]

# A weak password is refused before any change is made.
def testResetWeakPasswordChangesNothing(userId):
    token = loginNow().token
    done, error = service.resetPassword(EMAIL, "short")
    assert (done, error["fields"]) == (None, {"newPassword": "too_short"})
    assert resolveSession(token) is not None
    assert loginNow().token
