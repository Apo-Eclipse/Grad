"""Goals database operations."""

import logging
from django.utils import timezone
from typing import Any, Dict, Optional

from ninja import Router, Query

from core.models import Goal
from features.auth.api import AuthBearer
from core.utils.responses import success_response, error_response
from .schemas import (
    GoalCreateSchema,
    GoalUpdateSchema,
    GoalResponse,
    GoalListResponse,
)

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


# Fields for goal queries
GOAL_FIELDS = (
    "id",
    "user_id",
    "goal_name",
    "description",
    "target",
    "start_date",
    "due_date",
    "active",
    "saved_amount",
    "icon",
    "color",
    "plan",
    "created_at",
    "updated_at",
)


def _compute_goal_stats(goal: Dict[str, Any]) -> Dict[str, Any]:
    """Compute derived fields for a goal dict."""
    # Ensure numbers are float
    target = float(goal["target"]) if goal["target"] else 0.0
    saved = float(goal.get("saved_amount", 0.0))

    # Metadata
    # display_info = parse_budget_display_info(goal["description"])

    # Progress
    progress = (saved / target * 100) if target > 0 else 0.0

    # Days Remaining
    days_remaining = None
    if goal["due_date"]:
        today = timezone.localdate()
        delta = (goal["due_date"] - today).days
        days_remaining = max(0, delta)

    # Update dict
    goal["target"] = target
    goal["current_amount"] = saved  # Alias for frontend
    goal["saved_amount"] = saved
    goal["progress_percentage"] = round(progress, 1)
    goal["days_remaining"] = days_remaining

    # Metadata fields
    # goal["icon"] = display_info["icon"]
    # goal["color"] = display_info["color"]
    # goal["clean_description"] = display_info["description"]
    goal["clean_description"] = goal["description"]

    return goal


@router.get("/", response=GoalListResponse)
def get_goals(request, active: Optional[bool] = Query(None)):
    """Retrieve goals for a user."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active

    queryset = Goal.objects.filter(**filters)

    # Sorting
    if active is False:
        queryset = queryset.order_by("-updated_at")
    else:
        # Default sort (created_at desc was previous default)
        queryset = queryset.order_by("-created_at")

    goals = queryset.values(*GOAL_FIELDS)

    result = [_compute_goal_stats(g) for g in goals]
    return success_response(result)


@router.get("/{goal_id}", response=GoalResponse)
def get_goal(request, goal_id: int):
    """Get a single goal."""
    goal = (
        Goal.objects.filter(id=goal_id, user_id=request.user.id)
        .values(*GOAL_FIELDS)
        .first()
    )
    if not goal:
        return error_response("Goal not found", code=404)

    return success_response(_compute_goal_stats(goal))


@router.post("/", response=GoalResponse)
def create_goal(request, payload: GoalCreateSchema):
    """Create a new goal."""
    try:
        goal = Goal.objects.create(
            user_id=request.user.id,
            goal_name=payload.name,  # Map name -> goal_name
            description=payload.description,
            target=payload.target,
            start_date=timezone.localdate(),
            due_date=payload.due_date,
            icon=payload.icon,
            color=payload.color,
            plan=payload.plan,
        )
        # Fetch created goal as dict
        created = Goal.objects.filter(id=goal.id).values(*GOAL_FIELDS).first()
        return success_response(
            _compute_goal_stats(created), "Goal created successfully"
        )
    except Exception as e:
        logger.exception("Failed to create goal")
        return error_response(f"Failed to create goal: {e}")


@router.put("/{goal_id}", response=GoalResponse)
def update_goal(request, goal_id: int, payload: GoalUpdateSchema):
    """Update an existing goal."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return error_response("No fields provided for update")

    updates["updated_at"] = timezone.now()

    # Map name -> goal_name
    if "name" in updates:
        updates["goal_name"] = updates.pop("name")

    # Map status -> active
    if "status" in updates:
        status = updates.pop("status")
        if status == "active":
            updates["active"] = True
        elif status in ["archive", "deleted"]:
            updates["active"] = False

    try:
        rows_affected = Goal.objects.filter(id=goal_id, user_id=request.user.id).update(
            **updates
        )
        if rows_affected == 0:
            return error_response("Goal not found", code=404)

        goal = Goal.objects.filter(id=goal_id).values(*GOAL_FIELDS).first()
        return success_response(_compute_goal_stats(goal), "Goal updated successfully")
    except Exception as e:
        logger.exception("Failed to update goal")
        return error_response(f"Failed to update goal: {e}")


@router.delete("/{goal_id}", response=GoalResponse)
def delete_goal(request, goal_id: int):
    """Soft delete a goal."""
    try:
        rows_affected = Goal.objects.filter(id=goal_id, user_id=request.user.id).update(
            active=False, updated_at=timezone.now()
        )
        if rows_affected == 0:
            return error_response("Goal not found", code=404)

        return success_response(None, "Goal deactivated successfully")
    except Exception as e:
        logger.exception("Failed to delete goal")
        return error_response(f"Failed to delete goal: {e}")
