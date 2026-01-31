"""Goals database operations - CRUD only."""

import logging
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import F
from typing import Optional
from asgiref.sync import sync_to_async

from ninja import Router, Query
from core.models import Goal, Account
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


@sync_to_async
def _handle_goal_transaction(user_id: int, goal_id: int, amount: float, operation: str):
    """
    Sync helper to handle goal transactions atomically.
    Operation: "DEPOSIT" (Savings -> Goal) or "WITHDRAW" (Goal -> Savings)
    """
    with db_transaction.atomic():
        # 1. Fetch Goal
        goal = Goal.objects.select_for_update().filter(
            id=goal_id, user_id=user_id, active=True
        ).first()
        if not goal:
            return {"error": "Goal not found", "code": 404}

        # 2. Fetch Savings Account
        savings = Account.objects.select_for_update().filter(
            user_id=user_id, type="SAVINGS", active=True
        ).first()
        if not savings:
             return {"error": "No active Savings account found", "code": 400}

        amount_decimal = float(amount)
        
        if operation == "DEPOSIT":
            # Deduct from Savings, Add to Goal
            if float(savings.balance) < amount_decimal:
                return {
                    "error": f"Insufficient funds in Savings. Available: {savings.balance}",
                    "code": 400
                }
            savings.balance = float(savings.balance) - amount_decimal
            goal.saved_amount = float(goal.saved_amount) + amount_decimal
            
        elif operation == "WITHDRAW":
            # Deduct from Goal, Return to Savings
            if float(goal.saved_amount) < amount_decimal:
                return {
                    "error": f"Insufficient funds in Goal. Available: {goal.saved_amount}",
                    "code": 400
                }
            goal.saved_amount = float(goal.saved_amount) - amount_decimal
            savings.balance = float(savings.balance) + amount_decimal

        savings.save()
        goal.save()
        return {"goal": _format_goal(Goal.objects.filter(id=goal.id).values(*GOAL_FIELDS).first())}


@router.delete("/{goal_id}", response=GoalResponse)
async def delete_goal(request, goal_id: int):
    """Soft delete a goal. Refunds saved_amount to Savings Account."""
    @sync_to_async
    def _delete_logic():
        with db_transaction.atomic():
            goal = Goal.objects.select_for_update().filter(
                id=goal_id, user_id=request.user.id, active=True
            ).first()
            if not goal:
                return {"error": "Goal not found", "code": 404}

            if goal.saved_amount > 0:
                savings = Account.objects.select_for_update().filter(
                    user_id=request.user.id, type="SAVINGS", active=True
                ).first()
                if not savings:
                    return {"error": "Cannot refund: No Savings account", "code": 400}
                
                savings.balance = float(savings.balance) + float(goal.saved_amount)
                savings.save()
            
            goal.saved_amount = 0.0
            goal.active = False
            goal.updated_at = timezone.now()
            goal.save()
            return {"success": True}

    result = await _delete_logic()
    if "error" in result:
        return error_response(result["error"], code=result["code"])
    return success_response(None, "Goal deleted and funds refunded successfully")


@router.post("/{goal_id}/deposit", response=GoalResponse)
async def deposit_to_goal(request, goal_id: int, payload: GoalDepositSchema):
    """Add money to a goal (Deducts from Savings)."""
    result = await _handle_goal_transaction(
        request.user.id, goal_id, payload.amount, "DEPOSIT"
    )
    if "error" in result:
        return error_response(result["error"], code=result["code"])
    return success_response(result["goal"], "Funds deposited successfully")


@router.post("/{goal_id}/withdraw", response=GoalResponse)
async def withdraw_from_goal(request, goal_id: int, payload: GoalDepositSchema):
    """Withdraw money from a goal (Refunds to Savings)."""
    result = await _handle_goal_transaction(
        request.user.id, goal_id, payload.amount, "WITHDRAW"
    )
    if "error" in result:
        return error_response(result["error"], code=result["code"])
    return success_response(result["goal"], "Funds withdrawn successfully")
