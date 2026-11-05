from fastapi import APIRouter, Depends
from core.auth import ROLE_ADMIN, ROLE_MANAGER, AuthUser, requireRole
from core.error import raiseServiceError
from modules.ai import service
from modules.ai.schemas.request import AiQueryRequest
from modules.ai.schemas.response import AiQueryResponse

router = APIRouter(prefix="/ai", tags=["ai"])
requireReporter = requireRole(ROLE_ADMIN, ROLE_MANAGER)

# Answers one supported operations question from fixed database queries, worded by the model when it is available.
# The endpoint is synchronous so the blocking Bedrock call runs in the thread pool, off the event loop.
@router.post("/query", response_model=AiQueryResponse)
def query(body: AiQueryRequest, actor: AuthUser = Depends(requireReporter)):
    answer, error = service.answerQuestion(actor, body.question)
    if error:
        raiseServiceError(error)
    return answer


__all__ = ["router"]
