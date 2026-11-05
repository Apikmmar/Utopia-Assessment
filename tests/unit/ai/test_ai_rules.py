import json
from datetime import date, datetime, timezone
from uuid import uuid4
import pytest
from botocore.exceptions import ClientError, ReadTimeoutError
from core import config
from core.auth import AuthUser
from modules.ai import provider, service
from modules.ai.constants import MAX_OUTPUT_TOKENS, PAYLOAD_MAX_BYTES, SYSTEM_PROMPT, UNSUPPORTED_MESSAGE
from modules.ai.parser import matchTechnicians, parseQuestion
from modules.ai.period import resolvePeriod

TODAY = date(2026, 11, 5)
MANAGER = AuthUser(userId=uuid4(), name="Max", email="max@example.com", roleCode="manager")
TECHNICIAN = AuthUser(userId=uuid4(), name="Ali", email="ali@example.com", roleCode="technician")
TECHNICIANS = [{"user_id": 1, "name": "Ali Hassan"}, {"user_id": 2, "name": "Ali Rahman"}, {"user_id": 3, "name": "Bala"}]


# The three supported questions parse to their fixed intent and period, tolerating case, spacing, and one final "?".
@pytest.mark.parametrize("question, intent, period, name", [
    ("What jobs did technician Ali complete last week?", "technician_jobs", "last_week", "Ali"),
    ("  what JOBS did   Ali Hassan complete last week ", "technician_jobs", "last_week", "Ali Hassan"),
    ("Which technician completed the most jobs this week?", "top_technician", "this_week", None),
    ("HOW MANY JOBS WERE COMPLETED TODAY", "completed_count", "today", None),
])
def testParsesSupportedQuestions(question, intent, period, name):
    assert parseQuestion(question) == {"intent": intent, "period": period, "name": name}

# Paraphrases, other periods, extra clauses, and overlong names are not guessed at.
@pytest.mark.parametrize("question", [
    "What jobs did Ali complete this week?",
    "How many jobs were completed yesterday?",
    "Which technician completed the most jobs this week and why?",
    "How many jobs were completed today??",
    "Show me all customers",
    "What jobs did " + "A" * 101 + " complete last week?",
])
def testRejectsOtherQuestions(question):
    assert parseQuestion(question) is None

# An exact full name wins; otherwise every technician with that first name matches, so the caller can ask again.
def testMatchesTechnicianNames():
    assert [row["user_id"] for row in matchTechnicians("ali  hassan", TECHNICIANS)] == [1]
    assert [row["user_id"] for row in matchTechnicians("Ali", TECHNICIANS)] == [1, 2]
    assert [row["user_id"] for row in matchTechnicians("BALA", TECHNICIANS)] == [3]
    assert matchTechnicians("Chong", TECHNICIANS) == []

# Periods use Malaysian midnights: today, this Monday-to-Sunday week, and the week before.
def testResolvesPeriods():
    today = resolvePeriod("today", TODAY)
    assert (today["label"], today["start_utc"], today["end_utc"]) == (
        "5 Nov 2026", datetime(2026, 11, 4, 16, tzinfo=timezone.utc), datetime(2026, 11, 5, 16, tzinfo=timezone.utc),
    )
    thisWeek = resolvePeriod("this_week", TODAY)
    assert (thisWeek["label"], thisWeek["start_date"], thisWeek["end_date"]) == ("2 to 8 Nov 2026", date(2026, 11, 2), date(2026, 11, 8))
    lastWeek = resolvePeriod("last_week", TODAY)
    assert (lastWeek["label"], lastWeek["start_utc"]) == ("26 Oct to 1 Nov 2026", datetime(2026, 10, 25, 16, tzinfo=timezone.utc))

# Returns one parsed question and its period.
def parsedFor(question):
    parsed = parseQuestion(question)
    return parsed, resolvePeriod(parsed["period"], TODAY)

# Returns a technician-jobs result with the given number of listed jobs out of the total.
def jobsResult(listed, total):
    items = [{"order_id": uuid4(), "order_no": f"ORD-{n:06d}", "service_type": "Repair", "completed_at": datetime(2026, 10, 27, tzinfo=timezone.utc)}
             for n in range(listed)]
    return {"kind": "technician_jobs", "technician": {"user_id": uuid4(), "name": "Ali"}, "total": total, "items": items, "truncated": total > listed}

# Template answers state the facts for each intent, including none, ties, and a shortened list.
def testTemplateAnswers():
    parsed, period = parsedFor("What jobs did Ali complete last week?")
    assert service.templateAnswer(parsed, period, jobsResult(0, 0)) == "Ali completed no jobs last week (26 Oct to 1 Nov 2026)."
    assert service.templateAnswer(parsed, period, jobsResult(1, 1)) == "Ali completed 1 job last week (26 Oct to 1 Nov 2026): ORD-000000 (Repair)."
    assert service.templateAnswer(parsed, period, jobsResult(2, 25)).endswith("Showing the first 2.")
    parsed, period = parsedFor("Which technician completed the most jobs this week?")
    tie = {"kind": "top_technician", "jobs_completed": 3, "total": 2, "items": [{"user_id": 1, "name": "Ali"}, {"user_id": 2, "name": "Bala"}], "truncated": False}
    assert service.templateAnswer(parsed, period, tie) == "Ali, Bala tied for the most jobs this week (2 to 8 Nov 2026), with 3 jobs each."
    none = {"kind": "top_technician", "jobs_completed": 0, "total": 0, "items": [], "truncated": False}
    assert service.templateAnswer(parsed, period, none) == "No jobs were completed this week (2 to 8 Nov 2026), so there is no leader yet."
    parsed, period = parsedFor("How many jobs were completed today?")
    assert service.templateAnswer(parsed, period, {"kind": "completed_count", "total": 1}) == "1 job was completed today (5 Nov 2026)."

# The model sees names, order numbers, and counts but no ids, and a list too big for the payload is shortened while
# the total stays exact.
def testModelFactsCarryNoIdsAndStayBounded():
    parsed, period = parsedFor("What jobs did Ali complete last week?")
    facts = service.modelFacts(parsed, period, jobsResult(2, 2))
    assert facts["result"]["technician"] == "Ali" and "order_id" not in facts["result"]["items"][0]
    big = jobsResult(20, 400)
    for item in big["items"]:
        item["service_type"] = "x" * 1000
    bounded = service.modelFacts(parsed, period, big)
    assert len(json.dumps(bounded).encode()) <= PAYLOAD_MAX_BYTES
    assert bounded["result"]["total"] == 400 and bounded["result"]["truncated"] is True and len(bounded["result"]["items"]) < 20


class FakeClient:
    # Records the Converse call and returns or raises what the test set.
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.reply

# Returns a Converse response with the given text and stop reason.
def converseReply(text="Ali completed 2 jobs.", stopReason="end_turn"):
    return {"output": {"message": {"content": [{"text": text}]}}, "stopReason": stopReason, "usage": {"inputTokens": 100, "outputTokens": 20, "totalTokens": 120}}

# One bounded, non-streaming request carries the fixed instruction and the facts only, and the answer comes back
# with its token usage.
def testProviderSendsBoundedRequest():
    client = FakeClient(converseReply())
    answer = provider.BedrockProvider(client, "model-x").summarize({"question": "technician_jobs"})
    call = client.calls[0]
    assert call["modelId"] == "model-x" and call["system"] == [{"text": SYSTEM_PROMPT}]
    assert call["inferenceConfig"]["maxTokens"] == MAX_OUTPUT_TOKENS
    assert json.loads(call["messages"][0]["content"][0]["text"]) == {"question": "technician_jobs"}
    assert answer == {"text": "Ali completed 2 jobs.", "usage": {"input": 100, "output": 20, "total": 120}}

# Cut-off, empty, or oversized answers and provider errors become sanitized ProviderErrors.
@pytest.mark.parametrize("client, status, reason", [
    (FakeClient(converseReply(stopReason="max_tokens")), "error", "StopReason:max_tokens"),
    (FakeClient(converseReply(text="  ")), "error", "EmptyAnswer"),
    (FakeClient(converseReply(text="x" * 2001)), "error", "AnswerTooLong"),
    (FakeClient(error=ReadTimeoutError(endpoint_url="https://bedrock.example")), "timeout", "ReadTimeoutError"),
    (FakeClient(error=ClientError({"Error": {"Code": "AccessDeniedException", "Message": "secret detail"}}, "Converse")), "error", "AccessDeniedException"),
])
def testProviderFailures(client, status, reason):
    with pytest.raises(provider.ProviderError) as raised:
        provider.BedrockProvider(client, "model-x").summarize({})
    assert (raised.value.status, raised.value.reason) == (status, reason)

# AI is off by default; when on, the region and model id are required and the model id must fit the catalog.
def testAiSettings(monkeypatch):
    assert config.aiEnabled() is False and config.aiDailyRequestLimit() == 50
    monkeypatch.setenv("DATABASE_URL", "postgresql://user@host:5432/db")
    monkeypatch.setenv("DATABASE_PASSWORD", "secret")
    config.requireStartupSettings()
    monkeypatch.setenv("AI_ENABLED", "true")
    with pytest.raises(RuntimeError, match="AWS_REGION, AI_BEDROCK_MODEL_ID"):
        config.requireStartupSettings()
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    monkeypatch.setenv("AI_BEDROCK_MODEL_ID", "m" * 101)
    with pytest.raises(RuntimeError, match="at most 100"):
        config.requireStartupSettings()
    monkeypatch.setenv("AI_BEDROCK_MODEL_ID", "apac.anthropic.claude-haiku")
    config.requireStartupSettings()

# Technicians are refused, a disabled feature is unavailable, and an unsupported question gets guidance; none of
# these touch the database or the model.
def testRefusalsAndGuidanceNeedNoDatabase(monkeypatch):
    assert service.answerQuestion(TECHNICIAN, "How many jobs were completed today?")[1]["code"] == "FORBIDDEN"
    assert service.answerQuestion(MANAGER, "How many jobs were completed today?")[1]["code"] == "AI_UNAVAILABLE"
    monkeypatch.setenv("AI_ENABLED", "true")
    answer, error = service.answerQuestion(MANAGER, "Tell me a joke")
    assert error is None and answer["status"] == "unsupported" and answer["answer"] == UNSUPPORTED_MESSAGE and answer["result"] is None
