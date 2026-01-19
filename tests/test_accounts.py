from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Account, Transaction, Budget
from ninja.testing import TestClient
from features.crud.accounts.endpoints import router
from decimal import Decimal


class AccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client = TestClient(router)
        self.budget = Budget.objects.create(
            user=self.user, budget_name="Test Budget", total_limit=1000
        )

    def test_create_account(self):
        # Test creating a Regular account
        acc = Account.objects.create(
            user=self.user, name="Main Wrapper", type="REGULAR", balance=1000.00
        )
        self.assertEqual(acc.balance, 1000.00)
        self.assertEqual(acc.type, "REGULAR")

    def test_transfer_funds(self):
        # Create two accounts
        acc_a = Account.objects.create(
            user=self.user, name="A", type="REGULAR", balance=1000.00
        )
        acc_b = Account.objects.create(
            user=self.user, name="B", type="SAVINGS", balance=500.00
        )

        # Execute Transfer Logic manually (mimicking endpoint logic)
        amount = Decimal("200.00")

        # 1. Update In-Memory
        acc_a.balance -= amount
        acc_b.balance += amount
        acc_a.save()
        acc_b.save()

        # 2. Check DB
        acc_a.refresh_from_db()
        acc_b.refresh_from_db()

        self.assertEqual(acc_a.balance, Decimal("800.00"))
        self.assertEqual(acc_b.balance, Decimal("700.00"))

        # 3. Check Transaction Creation
        Transaction.objects.create(
            user=self.user,
            budget=self.budget,
            date="2024-01-01",
            amount=amount,
            account=acc_a,
            transfer_to=acc_b,
            type_spending="Transfer",
        )

        tx = Transaction.objects.get(account=acc_a)
        self.assertEqual(tx.transfer_to, acc_b)
        self.assertEqual(tx.amount, amount)
