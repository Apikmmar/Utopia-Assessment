import json
import time
from core import config
from core.auth import ROLE_ADMIN, ROLE_MANAGER
from core.businesstime import businessToday
from core.db import connection, transaction
from core.error import AI_UNAVAILABLE_CODE, AI_USAGE_LIMIT_CODE, FORBIDDEN_CODE, serviceError
from core.logger import getLogger
from core.request_context import currentRequestId
from modules.ai import parser, provider, repository
from modules.ai.constants import (
    AMBIGUOUS_TECHNICIAN_MESSAGE, FALLBACK_NOTICE, INTENT_COMPLETED_COUNT, INTENT_TECHNICIAN_JOBS, INTENT_TOP_TECHNICIAN, INVOCATION_SUCCESS,
    NOT_ALLOWED_MESSAGE, PAYLOAD_MAX_BYTES, PERIOD_TODAY, PROVIDER_NAME, ROW_LIMIT, SOURCE_AI, SOURCE_TEMPLATE, STATUS_ANSWERED,
    STATUS_CLARIFICATION, STATUS_UNSUPPORTED, UNAVAILABLE_MESSAGE, UNKNOWN_TECHNICIAN_MESSAGE, UNSUPPORTED_MESSAGE, USAGE_LIMIT_MESSAGE,
)
from modules.ai.period import resolvePeriod
from modules.user import service as userService

log = getLogger(__name__)

NOT_ALLOWED = serviceError(FORBIDDEN_CODE, NOT_ALLOWED_MESSAGE)
UNAVAILABLE = serviceError(AI_UNAVAILABLE_CODE, UNAVAILABLE_MESSAGE)
PERIOD_FIELDS = ("label", "start_date", "end_date")
PERIOD_WORDS = {"today": "today", "this_week": "this week", "last_week": "last week"}
JOB_FACT_FIELDS = ("order_no", "service_type", "completed_at")

# Returns a guidance answer that carries no period or result.
def guidance(status, answer):
    return {"status": status, "answer": answer, "summary_source": None, "notice": None, "period": None, "result": None}

# Returns the technician the name points at, or the clarification answer when it matches none or several.
def resolveTechnician(name, conn):
    matches = parser.matchTechnicians(name, userService.listTechnicians(conn))
    if not matches:
        return None, guidance(STATUS_CLARIFICATION, UNKNOWN_TECHNICIAN_MESSAGE.format(name=name))
    if len(matches) > 1:
        names = ", ".join(row["name"] for row in matches)
        return None, guidance(STATUS_CLARIFICATION, AMBIGUOUS_TECHNICIAN_MESSAGE.format(name=name, names=names))
    return {"user_id": matches[0]["user_id"], "name": matches[0]["name"]}, None

# Returns one technician's completed jobs in the period with the exact total, or a clarification answer.
def technicianJobsResult(name, start, end, conn):
    technician, clarification = resolveTechnician(name, conn)
    if clarification:
        return None, clarification
    rows = repository.technicianJobs(technician["user_id"], start, end, ROW_LIMIT, conn)
    total = rows[0]["total"] if rows else 0
    items = [
        {"order_id": row["service_order_id"], "order_no": row["order_no"], "service_type": row["service_type_name"], "completed_at": row["completed_at"]}
        for row in rows
    ]
    return {"kind": INTENT_TECHNICIAN_JOBS, "technician": technician, "total": total, "items": items, "truncated": total > len(items)}, None

# Returns the technicians tied for the most completions in the period with the winning count.
def topTechnicianResult(start, end, conn):
    rows = repository.topTechnicians(start, end, ROW_LIMIT, conn)
    total = rows[0]["total"] if rows else 0
    return {
        "kind": INTENT_TOP_TECHNICIAN, "jobs_completed": rows[0]["jobs"] if rows else 0, "total": total,
        "items": [{"user_id": row["user_id"], "name": row["name"]} for row in rows], "truncated": total > len(rows),
    }

# Returns the result for one parsed question from the fixed queries, or a clarification answer.
def retrieve(parsed, period, conn):
    start, end = period["start_utc"], period["end_utc"]
    if parsed["intent"] == INTENT_TECHNICIAN_JOBS:
        return technicianJobsResult(parsed["name"], start, end, conn)
    if parsed["intent"] == INTENT_TOP_TECHNICIAN:
        return topTechnicianResult(start, end, conn), None
    return {"kind": INTENT_COMPLETED_COUNT, "total": repository.completedCount(start, end, conn)}, None

# Returns "3 jobs" or "1 job".
def jobCount(count):
    return f"{count} job{'' if count == 1 else 's'}"

# Returns a plain answer written from the facts without the model, used for empty results and provider failures.
def templateAnswer(parsed, period, result):
    when = f"{PERIOD_WORDS[parsed['period']]} ({period['label']})"
    if result["kind"] == INTENT_TECHNICIAN_JOBS:
        name = result["technician"]["name"]
        if not result["total"]:
            return f"{name} completed no jobs {when}."
        listed = "; ".join(f"{item['order_no']} ({item['service_type']})" for item in result["items"])
        more = f" Showing the first {len(result['items'])}." if result["truncated"] else ""
        return f"{name} completed {jobCount(result['total'])} {when}: {listed}.{more}"
    if result["kind"] == INTENT_TOP_TECHNICIAN:
        if not result["total"]:
            return f"No jobs were completed {when}, so there is no leader yet."
        names = ", ".join(item["name"] for item in result["items"])
        if result["total"] == 1:
            return f"{names} completed the most jobs {when}, with {jobCount(result['jobs_completed'])}."
        shown = f" (showing {len(result['items'])} of {result['total']})" if result["truncated"] else ""
        return f"{names}{shown} tied for the most jobs {when}, with {jobCount(result['jobs_completed'])} each."
    verb = "was" if result["total"] == 1 else "were"
    return f"{jobCount(result['total']).capitalize()} {verb} completed {when}."

# Returns the facts the model may see: the intent, the period, and the result without ids, kept under the payload
# limit by shortening the listed items while the totals stay exact.
def modelFacts(parsed, period, result):
    facts = {"question": parsed["intent"], "period": {key: str(period[key]) for key in PERIOD_FIELDS}, "result": dict(result)}
    if result["kind"] == INTENT_TECHNICIAN_JOBS:
        facts["result"]["technician"] = result["technician"]["name"]
        facts["result"]["items"] = [{key: str(item[key]) for key in JOB_FACT_FIELDS} for item in result["items"]]
    elif result["kind"] == INTENT_TOP_TECHNICIAN:
        facts["result"]["items"] = [item["name"] for item in result["items"]]
    while len(json.dumps(facts).encode("utf-8")) > PAYLOAD_MAX_BYTES and facts["result"].get("items"):
        facts["result"]["items"] = facts["result"]["items"][:-1]
        facts["result"]["truncated"] = True
    return facts

# Returns the registered model row when a call is allowed, or the refusal: switched off, or over today's limit.
# The count is not locked, so concurrent requests can pass the limit by a few; this bounds a demo, not billing.
def checkAllowance(today):
    with transaction() as conn:
        modelRow = repository.ensureModel(PROVIDER_NAME, config.aiBedrockModelId(), conn)
        if not modelRow["is_active"]:
            return None, UNAVAILABLE
        limit = config.aiDailyRequestLimit()
        if repository.invocationsSince(resolvePeriod(PERIOD_TODAY, today)["start_utc"], conn) >= limit:
            return None, serviceError(AI_USAGE_LIMIT_CODE, USAGE_LIMIT_MESSAGE.format(limit=limit))
    return modelRow, None

# Records one model call with its outcome, latency, and any reported tokens.
def recordCall(actor, modelRow, outcome, latencyMs, reason, usage):
    with transaction() as conn:
        repository.insertInvocation({
            "llm_model_id": modelRow["llm_model_id"], "request_id": currentRequestId(), "status": outcome, "latency_ms": latencyMs,
            "error_message": reason, "created_by": actor.email, "updated_by": actor.email,
        }, conn)
        if usage:
            repository.insertTokenUsage({
                "model_id": config.aiBedrockModelId(), "input_token": usage["input"], "output_token": usage["output"],
                "total_token": usage["total"], "created_by": actor.email, "updated_by": actor.email,
            }, conn)

# Returns the model's summary of the facts, or None when the call failed, recording the call either way.
def summarize(actor, facts, modelRow, summaryProvider):
    started = time.monotonic()
    try:
        answer = summaryProvider.summarize(facts)
        outcome, reason, usage, text = INVOCATION_SUCCESS, None, answer["usage"], answer["text"]
    except provider.ProviderError as error:
        outcome, reason, usage, text = error.status, error.reason, error.usage, None
        log.warning("ai_summary_failed status=%s reason=%s", outcome, reason)
    recordCall(actor, modelRow, outcome, int((time.monotonic() - started) * 1000), reason, usage)
    return text

# Answers one supported operations question for an admin or manager and returns (answer, error). The facts come
# from fixed queries; the model only words them, at most once, with no transaction open during the call.
def answerQuestion(actor, question, today=None, summaryProvider=None):
    if actor.roleCode not in (ROLE_ADMIN, ROLE_MANAGER):
        return None, NOT_ALLOWED
    if not config.aiEnabled():
        return None, UNAVAILABLE
    parsed = parser.parseQuestion(question)
    if parsed is None:
        return guidance(STATUS_UNSUPPORTED, UNSUPPORTED_MESSAGE), None
    today = today or businessToday()
    period = resolvePeriod(parsed["period"], today)
    with connection() as conn:
        result, clarification = retrieve(parsed, period, conn)
    if clarification:
        return clarification, None
    answer = {
        "status": STATUS_ANSWERED, "answer": templateAnswer(parsed, period, result), "summary_source": SOURCE_TEMPLATE, "notice": None,
        "period": {key: period[key] for key in PERIOD_FIELDS}, "result": result,
    }
    if not result["total"]:
        return answer, None
    modelRow, error = checkAllowance(today)
    if error:
        return None, error
    text = summarize(actor, modelFacts(parsed, period, result), modelRow, summaryProvider or provider.getProvider())
    if text is None:
        return {**answer, "notice": FALLBACK_NOTICE}, None
    return {**answer, "answer": text, "summary_source": SOURCE_AI}, None


__all__ = ["answerQuestion", "modelFacts", "templateAnswer"]
