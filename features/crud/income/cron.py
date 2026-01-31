import logging
import calendar  # Move import to top
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from django_cron import CronJobBase, Schedule
from core.models import Income, Transaction

logger = logging.getLogger(__name__)


class RecurringIncomeJob(CronJobBase):
    RUN_EVERY_MINS = 1440  # Run once every 24 hours
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = "features.crud.income.cron.RecurringIncomeJob"

    def _get_next_payment_date(self, current_date, anchor_day):
        """
        Calculates the next payment date while preserving the 'anchor' day.
        Example: If anchor is 31st, it returns Feb 28th, then Mar 31st.
        """
        year = current_date.year
        month = current_date.month + 1

        # Handle Year Rollover (e.g., December to January)
        while month > 12:
            month -= 12
            year += 1

        # Get the last day of the target month
        _, last_day_of_month = calendar.monthrange(year, month)

        # Use the lesser of the anchor day or the month's last day
        # e.g., min(31, 28) = 28 for February
        target_day = min(anchor_day, last_day_of_month)

        return current_date.replace(year=year, month=month, day=target_day)

    def do(self):
        today = timezone.now().date()
        logger.info(f"Checking for recurring income due on or before {today}")

        due_incomes = Income.objects.filter(
            active=True, next_payment_date__lte=today, payment_day__isnull=False
        ).select_related("account", "user")

        count = 0
        for income in due_incomes:
            if not income.account:
                continue

            try:
                with transaction.atomic():
                    # 1. Add funds (Using F() to prevent race conditions)
                    income.account.balance = F("balance") + income.amount
                    income.account.save(update_fields=["balance"])

                    # Optional: Refresh if you need the exact number for logging,
                    # but usually not needed just for the Transaction creation below.
                    # income.account.refresh_from_db()

                    # 2. Create Transaction Record
                    Transaction.objects.create(
                        user=income.user,
                        transaction_type="DEPOSIT",
                        date=today,
                        amount=income.amount,
                        description=f"{income.type_income} Recurring Income",
                        account=income.account,
                        income_source=income,
                    )

                    # 3. Reschedule for next month
                    income.next_payment_date = self._get_next_payment_date(
                        income.next_payment_date, income.payment_day
                    )
                    income.save()

                    count += 1
                    logger.info(
                        f"Processed income {income.id} for user {income.user.username}"
                    )

            except Exception as e:
                # Log the full stack trace for debugging
                logger.error(
                    f"Failed to process income {income.id}: {e}", exc_info=True
                )

        return f"Processed {count} recurring incomes"
