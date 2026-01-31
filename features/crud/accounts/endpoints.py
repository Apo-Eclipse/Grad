"""Account management endpoints."""

from typing import List, Optional
from asgiref.sync import sync_to_async

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from ninja import Router, Schema
from features.auth.api import AuthBearer
from core.models import Account, Transaction

router = Router(auth=AuthBearer())


class AccountSchema(Schema):
    id: int
    name: str
    type: str  # REGULAR, SAVINGS
    balance: float


class TransferSchema(Schema):
    from_account_id: int
    to_account_id: int
    amount: float
    description: Optional[str] = None


@router.get("/", response=List[AccountSchema])
async def list_accounts(request, type: str = None):
    """List all active accounts for the user, optionally filtered by type."""
    qs = Account.objects.filter(user=request.user, active=True)
    if type:
        qs = qs.filter(type=type)

    accounts = [acc async for acc in qs.order_by("id")]
    return accounts


@router.post("/transfer", response={200: str, 400: str})
async def transfer_funds(request, payload: TransferSchema):
    """Transfer funds between accounts."""
    if payload.amount <= 0:
        return 400, "Amount must be positive."

    # Complex transactional logic with select_for_update - keep in sync_to_async
    @sync_to_async
    def perform_transfer():
        with transaction.atomic():
            try:
                from_acc = Account.objects.select_for_update().get(
                    id=payload.from_account_id, user=request.user, active=True
                )
                to_acc = Account.objects.select_for_update().get(
                    id=payload.to_account_id, user=request.user, active=True
                )
            except Account.DoesNotExist:
                return 400, "One or both accounts not found."

            if from_acc.id == to_acc.id:
                return 400, "Cannot transfer to the same account."

            # Update Balances
            from_acc.balance = F("balance") - payload.amount
            to_acc.balance = F("balance") + payload.amount

            from_acc.save()
            to_acc.save()

            from_acc.refresh_from_db()
            to_acc.refresh_from_db()

            # Create Transaction Record
            Transaction.objects.create(
                user=request.user,
                transaction_type=Transaction.TransactionType.TRANSFER,
                date=timezone.now().date(),
                amount=payload.amount,
                description=payload.description
                or f"Transfer from {from_acc.name} to {to_acc.name}",
                account=from_acc,
                transfer_to=to_acc,
            )

        return 200, "Transfer successful."

    return await perform_transfer()
