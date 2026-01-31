"""Goals database operations - CRUD only."""

import logging
from django.utils import timezone
from typing import Optional
from django.db.models import F

from ninja import Router, Query

from core.models import Goal
from features.auth.api import AuthBearer
from core.utils.responses import success_response, error_response
from .schemas import (
    GoalCreateSchema,
    GoalUpdateSchema,
    GoalResponse,
    GoalListResponse,
    GoalDepositSchema,
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


def _format_goal(goal: dict) -> dict:
    """Format goal dict for JSON response."""
    return {
        "id": goal["id"],
        "user_id": goal["user_id"],
        "goal_name": goal["goal_name"],
        "description": goal.get("description"),
        "target": float(goal["target"]) if goal["target"] else 0.0,
        "saved_amount": float(goal.get("saved_amount", 0.0)),
        "start_date": goal.get("start_date"),
        "due_date": goal.get("due_date"),
        "icon": goal.get("icon"),
        "color": goal.get("color"),
        "plan": goal.get("plan"),
        "active": goal.get("active", True),
        "created_at": goal["created_at"],
        "updated_at": goal.get("updated_at"),
    }


@router.get("/", response=GoalListResponse)
async def get_goals(request, active: Optional[bool] = Query(None)):
    """Retrieve goals for a user (raw data)."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active

    queryset = Goal.objects.filter(**filters)
    if active is False:
        queryset = queryset.order_by("-updated_at")
    else:
        queryset = queryset.order_by("-created_at")

    goals = [g async for g in queryset.values(*GOAL_FIELDS)]
    result = [_format_goal(g) for g in goals]
    return success_response(result)


@router.get("/{goal_id}", response=GoalResponse)
async def get_goal(request, goal_id: int):
    """Get a single goal (raw data)."""
    goal = await (
        Goal.objects.filter(id=goal_id, user_id=request.user.id)
        .values(*GOAL_FIELDS)
        .afirst()
    )
    if not goal:
        return error_response("Goal not found", code=404)
    return success_response(_format_goal(goal))


@router.post("/", response=GoalResponse)
async def create_goal(request, payload: GoalCreateSchema):
    """Create a new goal."""
    try:
        goal = await Goal.objects.acreate(
            user_id=request.user.id,
            goal_name=payload.name,
            description=payload.description,
            target=payload.target,
            start_date=timezone.localdate(),
            due_date=payload.due_date,
            icon=payload.icon,
            color=payload.color,
            plan=payload.plan,
        )
        created = await Goal.objects.filter(id=goal.id).values(*GOAL_FIELDS).afirst()
        return success_response(_format_goal(created), "Goal created successfully")
    except Exception as e:
        logger.exception("Failed to create goal")
        return error_response(f"Failed to create goal: {e}")


@router.put("/{goal_id}", response=GoalResponse)
async def update_goal(request, goal_id: int, payload: GoalUpdateSchema):
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
        rows_affected = await Goal.objects.filter(
            id=goal_id, user_id=request.user.id
        ).aupdate(**updates)
        if rows_affected == 0:
            return error_response("Goal not found", code=404)
        goal = await Goal.objects.filter(id=goal_id).values(*GOAL_FIELDS).afirst()
        return success_response(_format_goal(goal), "Goal updated successfully")
    except Exception as e:
        logger.exception("Failed to update goal")
        return error_response(f"Failed to update goal: {e}")


@router.delete("/{goal_id}", response=GoalResponse)
async def delete_goal(request, goal_id: int):
    """Soft delete a goal."""
    try:
        rows_affected = await Goal.objects.filter(
            id=goal_id, user_id=request.user.id
        ).aupdate(active=False, updated_at=timezone.now())
        if rows_affected == 0:
            return error_response("Goal not found", code=404)
        return success_response(None, "Goal deactivated successfully")
    except Exception as e:
        logger.exception("Failed to delete goal")
        return error_response(f"Failed to delete goal: {e}")


@router.post("/{goal_id}/deposit", response=GoalResponse)
async def deposit_to_goal(request, goal_id: int, payload: GoalDepositSchema):
    """Add money to a goal (atomic update)."""
    try:
        goal_exists = await Goal.objects.filter(
            id=goal_id, user_id=request.user.id
        ).aexists()
        if not goal_exists:
            return error_response("Goal not found", code=404)

        await Goal.objects.filter(id=goal_id, user_id=request.user.id).aupdate(
            saved_amount=F("saved_amount") + payload.amount, updated_at=timezone.now()
        )
        updated_goal = (
            await Goal.objects.filter(id=goal_id).values(*GOAL_FIELDS).afirst()
        )
        return success_response(
            _format_goal(updated_goal), "Funds deposited successfully"
        )
    except Exception as e:
        logger.exception("Failed to deposit to goal")
        return error_response(f"Failed to deposit to goal: {e}")
