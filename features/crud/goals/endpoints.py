"""Goals database operations - CRUD only."""

import logging
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import F
from typing import Optional

from ninja import Router, Query

from core.models import Goal, Account
from features.auth.api import AuthBearer
from core.utils.responses import success_response, error_response
from .schemas import (
    GoalCreateSchema,
    GoalUpdateSchema,
    GoalResponse,
    GoalListResponse,
    GoalContributionSchema,
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
def get_goals(request, active: Optional[bool] = Query(None)):
    """Retrieve goals for a user (raw data)."""
    filters = {"user_id": request.user.id}
    if active is not None:
        filters["active"] = active

    queryset = Goal.objects.filter(**filters)

    # Sorting
    if active is False:
        queryset = queryset.order_by("-updated_at")
    else:
        queryset = queryset.order_by("-created_at")

    goals = queryset.values(*GOAL_FIELDS)
    result = [_format_goal(g) for g in goals]
    return success_response(result)


@router.get("/{goal_id}", response=GoalResponse)
def get_goal(request, goal_id: int):
    """Get a single goal (raw data)."""
    goal = (
        Goal.objects.filter(id=goal_id, user_id=request.user.id)
        .values(*GOAL_FIELDS)
        .first()
    )
    if not goal:
        return error_response("Goal not found", code=404)

    return success_response(_format_goal(goal))


@router.post("/", response=GoalResponse)
def create_goal(request, payload: GoalCreateSchema):
    """Create a new goal."""
    try:
        goal = Goal.objects.create(
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
        created = Goal.objects.filter(id=goal.id).values(*GOAL_FIELDS).first()
        return success_response(_format_goal(created), "Goal created successfully")
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
        return success_response(_format_goal(goal), "Goal updated successfully")
    except Exception as e:
        logger.exception("Failed to update goal")
        return error_response(f"Failed to update goal: {e}")


@router.delete("/{goal_id}", response=GoalResponse)
def delete_goal(request, goal_id: int):
    """Soft delete a goal. Refunds saved_amount to Savings Account."""
    try:
        with db_transaction.atomic():
            # 1. Fetch the goal
            goal = Goal.objects.select_for_update().filter(
                id=goal_id, user_id=request.user.id, active=True
            ).first()

            if not goal:
                return error_response("Goal not found", code=404)

            # 2. Refund logic if there is money saved
            if goal.saved_amount > 0:
                try:
                    savings_acc = Account.objects.select_for_update().get(
                        user_id=request.user.id, type="SAVINGS", active=True
                    )
                    savings_acc.balance = F("balance") + goal.saved_amount
                    savings_acc.save(update_fields=["balance"])
                    
                    # Reset goal saved amount to 0 since funds are moved
                    goal.saved_amount = 0.0
                    
                except Account.DoesNotExist:
                    # If no savings account, we can either error out or just delete.
                    # Given the "Bank" model, a user should have one. 
                    # If missing, we log a warning but proceed with deletion (or error to protect funds).
                    # Safest approach: Error to prevent fund loss.
                    return error_response(
                        "Cannot refund saved amount: No active Savings account found.", 
                        code=400
                    )
                except Account.MultipleObjectsReturned:
                     # Fallback: take the first one
                    savings_acc = Account.objects.select_for_update().filter(
                        user_id=request.user.id, type="SAVINGS", active=True
                    ).first()
                    if savings_acc:
                        savings_acc.balance = F("balance") + goal.saved_amount
                        savings_acc.save(update_fields=["balance"])
                        goal.saved_amount = 0.0

            # 3. Soft Delete
            goal.active = False
            goal.updated_at = timezone.now()
            goal.save(update_fields=["active", "updated_at", "saved_amount"])

        return success_response(None, "Goal deleted and funds refunded successfully")

    except Exception as e:
        logger.exception("Failed to delete goal")
        return error_response(f"Failed to delete goal: {e}")


@router.post("/{goal_id}/contribute", response=GoalResponse)
def contribute_to_goal(request, goal_id: int, payload: GoalContributionSchema):
    """
    Set the Goal's saved_amount to the provided payload.amount.
    Automatically adjusts Savings Account balance:
    - If increasing goal amount: Deduct from Savings (check balance).
    - If decreasing goal amount: Refund to Savings.
    """
    if payload.amount < 0:
        return error_response("Amount cannot be negative", code=400)

    try:
        with db_transaction.atomic():
            # 1. Fetch Savings Account
            # ... (Reuse existing logic)
            try:
                savings_acc = Account.objects.select_for_update().get(
                    user_id=request.user.id, type="SAVINGS", active=True
                )
            except Account.DoesNotExist:
                return error_response("No active Savings account found for this user", code=404)
            except Account.MultipleObjectsReturned:
                savings_acc = (
                    Account.objects.select_for_update()
                    .filter(user_id=request.user.id, type="SAVINGS", active=True)
                    .first()
                )
                if not savings_acc:
                    return error_response("No active Savings account found", code=404)

            # 2. Fetch Goal
            try:
                goal = Goal.objects.select_for_update().get(
                    id=goal_id, user_id=request.user.id, active=True
                )
            except Goal.DoesNotExist:
                return error_response("Active goal not found", code=404)

            # 3. Calculate Difference
            current_saved = float(goal.saved_amount)
            new_saved = payload.amount
            difference = new_saved - current_saved

            if difference == 0:
                return success_response(_format_goal(Goal.objects.filter(id=goal.id).values(*GOAL_FIELDS).first()), "No change in amount")

            # 4. Handle Funds Transfer
            if difference > 0:
                # Increasing goal -> Deduct from Savings
                if savings_acc.balance < difference:
                    return error_response(
                        f"Insufficient funds in Savings. Needed: {difference:.2f}, Available: {float(savings_acc.balance):.2f}",
                        code=400,
                    )
                savings_acc.balance = F("balance") - difference
            
            else:
                # Decreasing goal -> Refund to Savings
                # difference is negative, so substracting it adds to balance? 
                # No, standard logic: balance += abs(diff)
                savings_acc.balance = F("balance") + abs(difference)

            # 5. Update Goal
            goal.saved_amount = new_saved
            
            savings_acc.save(update_fields=["balance"])
            goal.save(update_fields=["saved_amount"])

            # Refresh goal
            goal.refresh_from_db()

            msg = "Funds added to goal" if difference > 0 else "Funds returned to savings"
            return success_response(
                _format_goal(
                    Goal.objects.filter(id=goal.id).values(*GOAL_FIELDS).first()
                ),
                msg,
            )

    except Exception as e:
        logger.exception("Failed to update goal savings")
        return error_response(f"Failed to update goal savings: {e}")

