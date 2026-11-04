import uuid
import pytest
from core.auth import AuthUser
from modules.order.constants import ORDER_STATUSES, TRANSITIONS
from modules.order.service import canTransition

TECH_ID = uuid.uuid4()
OTHER_TECH_ID = uuid.uuid4()
ROLES = ("admin", "technician", "manager")
ORDER = {"assigned_technician_id": TECH_ID}

# Returns an actor with the given role, the assigned technician's id for technicians.
def actor(roleCode, userId=TECH_ID):
    return AuthUser(userId=userId, name="User", email="user@example.com", roleCode=roleCode)

# Every pair of statuses for every role is allowed exactly when the transition table names that role.
@pytest.mark.parametrize("fromStatus", ORDER_STATUSES)
@pytest.mark.parametrize("toStatus", ORDER_STATUSES)
@pytest.mark.parametrize("role", ROLES)
def testTransitionTable(fromStatus, toStatus, role):
    assert canTransition(fromStatus, toStatus, actor(role), ORDER) is (TRANSITIONS.get((fromStatus, toStatus)) == role)

# The workflow is the single forward chain from the planning document.
def testWorkflowChain():
    assert list(TRANSITIONS) == [
        ("new", "assigned"), ("assigned", "in_progress"), ("in_progress", "job_done"), ("job_done", "reviewed"), ("reviewed", "closed"),
    ]

# A technician who is not the assigned one can never move the order.
@pytest.mark.parametrize("fromStatus,toStatus", [("assigned", "in_progress"), ("in_progress", "job_done")])
def testOnlyAssignedTechnician(fromStatus, toStatus):
    assert canTransition(fromStatus, toStatus, actor("technician"), ORDER) is True
    assert canTransition(fromStatus, toStatus, actor("technician", OTHER_TECH_ID), ORDER) is False
    assert canTransition(fromStatus, toStatus, actor("technician"), {"assigned_technician_id": None}) is False
