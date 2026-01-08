"""Goals database operations."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ninja import Router, Query

from ..models import Goal
from ..core.responses import success_response, error_response
from .schemas import GoalCreateSchema, GoalUpdateSchema

logger = logging.getLogger(__name__)
router = Router()


def _goal_to_dict(goal: Goal) -> Dict[str, Any]:
    """Convert Goal model instance to dictionary."""
    return {
        "id": goal.id,
        "user_id": goal.user_id,
        "goal_name": goal.goal_name,
        "description": goal.description,
        "target": float(goal.target) if goal.target else None,
        "start_date": goal.start_date,
        "due_date": goal.due_date,
        "status": goal.status,
        "plan": goal.plan,
        "created_at": goal.created_at,
        "updated_at": goal.updated_at,
    }


@router.get("/", response=Dict[str, Any])
def get_goals(request, user_id: int = Query(...), status: Optional[str] = Query(None)):
    """Retrieve goals for a user."""
    queryset = Goal.objects.filter(user_id=user_id)

    if status:
        queryset = queryset.filter(status=status)

    goals = queryset.order_by("-created_at").values(
        "id",
        "user_id",
        "goal_name",
        "description",
        "target",
        "start_date",
        "due_date",
        "status",
        "plan",
        "created_at",
        "updated_at",
    )
    return success_response(list(goals))


@router.get("/{goal_id}", response=Dict[str, Any])
def get_goal(request, goal_id: int):
    """Get a single goal."""
    try:
        goal = Goal.objects.get(id=goal_id)
        return success_response(_goal_to_dict(goal))
    except Goal.DoesNotExist:
        return error_response("Goal not found", code=404)


@router.post("/", response=Dict[str, Any])
def create_goal(request, payload: GoalCreateSchema):
    """Create a new goal."""
    try:
        goal = Goal.objects.create(
            user_id=payload.user_id,
            goal_name=payload.goal_name,
            description=payload.description,
            target=payload.target,
            start_date=payload.start_date,
            due_date=payload.due_date,
            status=payload.status,
            plan=payload.plan,
        )
        return success_response(_goal_to_dict(goal), "Goal created successfully")
    except Exception as e:
        logger.exception("Failed to create goal")
        return error_response(f"Failed to create goal: {e}")


@router.put("/{goal_id}", response=Dict[str, Any])
def update_goal(request, goal_id: int, payload: GoalUpdateSchema):
    """Update an existing goal."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    updates["updated_at"] = datetime.now()

    try:
        rows_affected = Goal.objects.filter(id=goal_id).update(**updates)
        if rows_affected == 0:
            return error_response("Goal not found", code=404)

        goal = Goal.objects.get(id=goal_id)
        return success_response(_goal_to_dict(goal), "Goal updated successfully")
    except Goal.DoesNotExist:
        return error_response("Goal not found", code=404)
    except Exception as e:
        logger.exception("Failed to update goal")
        return error_response(f"Failed to update goal: {e}")


@router.delete("/{goal_id}", response=Dict[str, Any])
def delete_goal(request, goal_id: int):
    """Soft delete a goal."""
    try:
        rows_affected = Goal.objects.filter(id=goal_id).update(
            status="inactive", updated_at=datetime.now()
        )
        if rows_affected == 0:
            return error_response("Goal not found", code=404)

        return success_response(None, "Goal deactivated successfully")
    except Exception as e:
        logger.exception("Failed to delete goal")
        return error_response(f"Failed to delete goal: {e}")
