import re
from modules.ai.constants import (
    INTENT_COMPLETED_COUNT, INTENT_TECHNICIAN_JOBS, INTENT_TOP_TECHNICIAN, NAME_MAX_LENGTH, PERIOD_LAST_WEEK, PERIOD_THIS_WEEK,
    PERIOD_TODAY,
)

TECHNICIAN_JOBS = re.compile(r"what jobs did (?:technician )?(?P<name>.+?) complete last week")
TOP_TECHNICIAN = re.compile(r"which technician completed the most jobs this week")
COMPLETED_COUNT = re.compile(r"how many jobs were completed today")

# Collapses whitespace and drops one trailing question mark, keeping the original case.
def collapse(question):
    text = " ".join(question.split())
    return text[:-1].rstrip() if text.endswith("?") else text

# Returns the question in the form the patterns match: collapsed and lowercased, so only those differences are
# tolerated.
def normalize(question):
    return collapse(question).lower()

# Returns {intent, period, name} for one of the three supported questions, or None for anything else. The name keeps
# the spelling the user typed.
def parseQuestion(question):
    original = collapse(question)
    text = original.lower()
    if TOP_TECHNICIAN.fullmatch(text):
        return {"intent": INTENT_TOP_TECHNICIAN, "period": PERIOD_THIS_WEEK, "name": None}
    if COMPLETED_COUNT.fullmatch(text):
        return {"intent": INTENT_COMPLETED_COUNT, "period": PERIOD_TODAY, "name": None}
    match = TECHNICIAN_JOBS.fullmatch(text)
    if match and len(match.group("name")) <= NAME_MAX_LENGTH:
        name = original[match.start("name"):match.end("name")] if len(original) == len(text) else match.group("name")
        return {"intent": INTENT_TECHNICIAN_JOBS, "period": PERIOD_LAST_WEEK, "name": name}
    return None

# Returns the technicians a name points at: case-insensitive exact full-name matches, else unique-or-not first-name
# matches. The caller treats one match as resolved and several as ambiguous.
def matchTechnicians(name, technicians):
    wanted = " ".join(name.split()).lower()
    exact = [row for row in technicians if " ".join(row["name"].split()).lower() == wanted]
    if exact:
        return exact
    return [row for row in technicians if row["name"].split() and row["name"].split()[0].lower() == wanted]


__all__ = ["collapse", "matchTechnicians", "normalize", "parseQuestion"]
