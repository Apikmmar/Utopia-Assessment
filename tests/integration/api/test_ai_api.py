from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from modules.ai import provider as aiProvider
from tests.support import STATE_HEADERS

EMAILS = {
    "admin": "admin.ai.api@example.com", "manager": "manager.ai.api@example.com", "techA": "tom.ai.api@example.com",
    "techB": "bala.ai.api@example.com", "techC": "tomlee.ai.api@example.com",
}
JOBS_QUESTION = "What jobs did technician Tom Tech complete last week?"
TOP_QUESTION = "Which technician completed the most jobs this week?"
COUNT_QUESTION = "How many jobs were completed today?"
INSERT_COMPLETED_ORDERS = text(
    "WITH orders AS ("
    " INSERT INTO service_order (customer_name, customer_phone, address, problem_description, service_type_id, quoted_price, "
    " assigned_technician_id, status, created_by_id) "
    " SELECT 'Siti Customer', '60123456789', 'No 1, Jalan Damai, KL', 'Aircond leaking', service_type_id, 150, :technicianId, :status, :adminId "
    " FROM service_type, generate_series(1, :count) WHERE service_type_code = 'repair' RETURNING service_order_id) "
    "INSERT INTO order_completion (service_order_id, technician_id, work_done, quoted_price, extra_charges, final_amount, completed_at) "
    "SELECT service_order_id, :technicianId, 'Done', 150, 0, 150, :completedAt FROM orders"
)


class FakeProvider:
    # Stands in for Bedrock: records the facts it was given and answers or fails as the test set.
    def __init__(self):
        self.calls = []
        self.error = None

    def summarize(self, facts):
        self.calls.append(facts)
        if self.error:
            raise self.error
        return {"text": f"AI summary of {facts['question']}.", "usage": {"input": 50, "output": 10, "total": 60}}


# Switches AI on with test settings and replaces only the Bedrock boundary.
@pytest.fixture
def fakeProvider(monkeypatch):
    fake = FakeProvider()
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    monkeypatch.setenv("AI_BEDROCK_MODEL_ID", "test-haiku")
    monkeypatch.setattr(aiProvider, "getProvider", lambda: fake)
    return fake

# Users for every role, with two technicians who share the first name Tom.
@pytest.fixture
def world(appDb, seedUser):
    return {
        "admin": seedUser(EMAILS["admin"], "admin", name="Ada Admin"),
        "manager": seedUser(EMAILS["manager"], "manager", name="Max Manager"),
        "techA": seedUser(EMAILS["techA"], "technician", name="Tom Tech", phone="60111111111"),
        "techB": seedUser(EMAILS["techB"], "technician", name="Bala Tech", phone="60122222222"),
        "techC": seedUser(EMAILS["techC"], "technician", name="Tom Lee", phone="60133333333"),
    }

# Inserts completed orders for one technician at one instant.
def addCompletions(appDb, world, technician, count, completedAt, status="closed"):
    with appDb.begin() as conn:
        conn.execute(INSERT_COMPLETED_ORDERS, {
            "technicianId": world[technician], "adminId": world["admin"], "status": status, "count": count, "completedAt": completedAt,
        })

# Asks one question as the client.
def ask(client, question):
    return client.post("/ai/query", json={"question": question}, headers=STATE_HEADERS)

# Admins and managers may ask; technicians are refused, anonymous callers are 401, bad bodies are 422, and a
# disabled feature is 503.
def testAccessValidationAndDisabled(world, loggedIn, app, monkeypatch):
    manager = loggedIn(EMAILS["manager"])
    assert ask(manager, COUNT_QUESTION).json()["code"] == "AI_UNAVAILABLE"
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    monkeypatch.setenv("AI_BEDROCK_MODEL_ID", "test-haiku")
    assert ask(loggedIn(EMAILS["admin"]), "Tell me a joke").json()["status"] == "unsupported"
    assert ask(loggedIn(EMAILS["techA"]), COUNT_QUESTION).json()["code"] == "FORBIDDEN"
    assert ask(TestClient(app), COUNT_QUESTION).status_code == 401
    blank = ask(manager, "   ")
    assert blank.status_code == 422 and "question" in blank.json()["fields"]
    assert manager.post("/ai/query", json={"question": COUNT_QUESTION, "sql": "x"}, headers=STATE_HEADERS).status_code == 422

# The three questions answer from the database with a model summary: a truncated job list for last week, a tie for
# this week, and today's count. Each call is recorded with its tokens.
def testAnswersTheThreeQuestions(appDb, world, loggedIn, fakeProvider, scalar):
    now = datetime.now(timezone.utc)
    addCompletions(appDb, world, "techA", 21, now - timedelta(days=7))
    addCompletions(appDb, world, "techA", 2, now, status="job_done")
    addCompletions(appDb, world, "techB", 2, now, status="reviewed")
    manager = loggedIn(EMAILS["manager"])

    jobs = ask(manager, JOBS_QUESTION).json()
    assert (jobs["status"], jobs["summarySource"], jobs["answer"]) == ("answered", "ai", "AI summary of technician_jobs.")
    assert jobs["result"]["technician"] == {"userId": str(world["techA"]), "name": "Tom Tech"}
    assert (jobs["result"]["total"], len(jobs["result"]["items"]), jobs["result"]["truncated"]) == (21, 20, True)
    assert jobs["result"]["items"][0]["orderNo"].startswith("ORD-") and jobs["result"]["items"][0]["serviceType"] == "Repair"

    top = ask(manager, TOP_QUESTION).json()["result"]
    assert (top["jobsCompleted"], top["total"], [item["name"] for item in top["items"]]) == (2, 2, ["Bala Tech", "Tom Tech"])

    count = ask(manager, COUNT_QUESTION).json()
    assert count["result"] == {"kind": "completed_count", "total": 4} and count["period"]["startDate"] == count["period"]["endDate"]

    sent = fakeProvider.calls[0]
    assert sent["result"]["technician"] == "Tom Tech" and "orderId" not in sent["result"]["items"][0] and "order_id" not in sent["result"]["items"][0]
    assert scalar("SELECT count(*) FROM llm_invocation WHERE status = 'success'") == 3
    assert scalar("SELECT sum(total_token) FROM token_usage WHERE model_id = 'test-haiku'") == 180

# Unknown and ambiguous names ask again and an empty period answers from a template, all without the model; a
# provider failure falls back to the database facts; and the daily limit refuses further calls.
def testClarificationFallbackAndLimit(appDb, world, loggedIn, fakeProvider, scalar, monkeypatch):
    manager = loggedIn(EMAILS["manager"])
    unknown = ask(manager, "What jobs did Chong complete last week?").json()
    assert unknown["status"] == "clarification_required" and unknown["result"] is None
    ambiguous = ask(manager, "What jobs did Tom complete last week?").json()
    assert ambiguous["status"] == "clarification_required" and "Tom Lee, Tom Tech" in ambiguous["answer"]
    empty = ask(manager, COUNT_QUESTION).json()
    assert (empty["summarySource"], empty["result"]["total"], empty["notice"]) == ("template", 0, None)
    assert fakeProvider.calls == []

    addCompletions(appDb, world, "techB", 1, datetime.now(timezone.utc))
    fakeProvider.error = aiProvider.ProviderError("timeout", "ReadTimeoutError")
    fallback = ask(manager, COUNT_QUESTION).json()
    assert (fallback["summarySource"], fallback["notice"]) == ("template", "AI summary unavailable. Showing database results.")
    assert fallback["answer"].startswith("1 job was completed today")
    assert scalar("SELECT error_message FROM llm_invocation WHERE status = 'timeout'") == "ReadTimeoutError"

    monkeypatch.setenv("AI_DAILY_REQUEST_LIMIT", "1")
    limited = ask(manager, COUNT_QUESTION)
    assert limited.status_code == 429 and limited.json()["code"] == "AI_USAGE_LIMIT"
    assert len(fakeProvider.calls) == 1
