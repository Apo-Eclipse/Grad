"""Goals database operations."""

import logging
from django.utils import timezone
from typing import Any, Dict, Optional

from ninja import Router, Query

from core.models import Goal
from core.utils.responses import success_response, error_response
from core.schemas.database import GoalCreateSchema, GoalUpdateSchema

logger = logging.getLogger(__name__)
router = Router()


# Fields for goal queries
GOAL_FIELDS = (
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


def _format_goal(goal: Dict[str, Any]) -> Dict[str, Any]:
    """Format goal dict for JSON response."""
    goal["target"] = float(goal["target"]) if goal["target"] else None
    return goal


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
    goal = (
        Goal.objects.filter(id=goal_id)
        .values(
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
        .first()
    )
    if not goal:
        return error_response("Goal not found", code=404)

    # Format target
    goal["target"] = float(goal["target"]) if goal["target"] else None
    return success_response(goal)


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
        # Fetch created goal as dict
        created = Goal.objects.filter(id=goal.id).values(*GOAL_FIELDS).first()
        return success_response(_format_goal(created), "Goal created successfully")
    except Exception as e:
        logger.exception("Failed to create goal")
        return error_response(f"Failed to create goal: {e}")


@router.put("/{goal_id}", response=Dict[str, Any])
def update_goal(request, goal_id: int, payload: GoalUpdateSchema):
    """Update an existing goal."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    updates["updated_at"] = timezone.now()

    try:
        rows_affected = Goal.objects.filter(id=goal_id).update(**updates)
        if rows_affected == 0:
            return error_response("Goal not found", code=404)

        goal = Goal.objects.filter(id=goal_id).values(*GOAL_FIELDS).first()
        return success_response(_format_goal(goal), "Goal updated successfully")
    except Exception as e:
        logger.exception("Failed to update goal")
        return error_response(f"Failed to update goal: {e}")


@router.delete("/{goal_id}", response=Dict[str, Any])
def delete_goal(request, goal_id: int):
    """Soft delete a goal."""
    try:
        rows_affected = Goal.objects.filter(id=goal_id).update(
            status="inactive", updated_at=timezone.now()
        )
        if rows_affected == 0:
            return error_response("Goal not found", code=404)

        return success_response(None, "Goal deactivated successfully")
    except Exception as e:
        logger.exception("Failed to delete goal")
        return error_response(f"Failed to delete goal: {e}")
