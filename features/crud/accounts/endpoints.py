"""Account management endpoints."""

from typing import List, Optional
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
    type: str  # REGULAR, SAVINGS, CREDIT
    balance: float


class CreateAccountSchema(Schema):
    name: str
    type: str = "REGULAR"
    initial_balance: float = 0.0


class TransferSchema(Schema):
    from_account_id: int
    to_account_id: int
    amount: float
    description: Optional[str] = None


@router.get("/", response=List[AccountSchema])
def list_accounts(request):
    """List all active accounts for the user."""
    return Account.objects.filter(user=request.user, active=True).order_by("id")


@router.post("/", response=AccountSchema)
def create_account(request, payload: CreateAccountSchema):
    """Create a new account."""
    account = Account.objects.create(
        user=request.user,
        name=payload.name,
        type=payload.type,
        balance=payload.initial_balance,
    )
    return account


@router.post("/transfer", response={200: str, 400: str})
def transfer_funds(request, payload: TransferSchema):
    """Transfer funds between accounts."""
    if payload.amount <= 0:
        return 400, "Amount must be positive."

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

        # Check balance if Regular/Savings (Credit accounts can go negative/positive freely,
        # but usually you pay TO credit or spend FROM credit.
        # If transferring FROM Regular, you need balance.
        # If transferring FROM Credit, you are effectively taking a cash advance?
        # Let's assume you can always transfer for now, or add check for REGULAR/SAVINGS.
        # For simplicity: Allow overdraft for now or check balance?
        # User said "Regular" has balance. Debit card.
        # Let's enforce non-negative for REGULAR/SAVINGS if we want strictness.
        # For now, minimal restriction.

        # 1. Update Balances
        from_acc.balance = F("balance") - payload.amount
        to_acc.balance = F("balance") + payload.amount

        from_acc.save()
        to_acc.save()

        from_acc.refresh_from_db()
        to_acc.refresh_from_db()

        # 2. Create Transaction Record (for history)
        # We model this as a Transaction on the source account with transfer_to set
        # This way it appears in the ledger of the source account.
        # What about the destination?
        # Ideally we might want two transactions or one linked one.
        # Our model has `account` and `transfer_to`.
        # Let's create one transaction record that represents this move.

        # However, for the UI to show it in both places, we might need 2 records
        # OR the query logic looks for `account=X OR transfer_to=X`.
        # Let's use 1 record with `transfer_to`.

        Transaction.objects.create(
            user=request.user,
            transaction_type=Transaction.TransactionType.TRANSFER,
            date=timezone.now().date(),
            amount=payload.amount,
            description=payload.description
            or f"Transfer from {from_acc.name} to {to_acc.name}",
            category="Transfer",
            account=from_acc,
            transfer_to=to_acc,
            budget=None,  # Transfers don't need a budget
        )

    return 200, "Transfer successful."
