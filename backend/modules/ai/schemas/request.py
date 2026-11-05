from typing import Annotated
from pydantic import StringConstraints
from core.schema import RequestModel
from modules.ai.constants import QUESTION_MAX_LENGTH


class AiQueryRequest(RequestModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=QUESTION_MAX_LENGTH)]


__all__ = ["AiQueryRequest"]
