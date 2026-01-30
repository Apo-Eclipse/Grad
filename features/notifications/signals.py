import logging
from decimal import Decimal
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.functions import Coalesce

from core.models import Transaction, Notification, Budget

logger = logging.getLogger(__name__)

# Warning thresholds
WARNING_THRESHOLD = Decimal('0.80')  # 80%
EXCEEDED_THRESHOLD = Decimal('1.00')  # 100%


@receiver(post_save, sender=Transaction)
def check_budget_limit(sender, instance, created, **kwargs):
    """
    Signal to check budget spending after a transaction is saved.
    - Warns at 80% spending (early warning)
    - Alerts when 100% limit is exceeded
    """
    if not instance.budget_id:
        return

    try:
        budget = Budget.objects.get(id=instance.budget_id)
        
        # Calculate total spent for this budget
        total_spent = Transaction.objects.filter(
            budget_id=budget.id, 
            active=True
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'))
        )['total']

        budget_limit = Decimal(str(budget.total_limit))
        spending_ratio = total_spent / budget_limit if budget_limit > 0 else Decimal('0')

        # Check if 100% exceeded
        if spending_ratio >= EXCEEDED_THRESHOLD:
            Notification.objects.create(
                user=instance.user,
                title="Budget Limit Exceeded",
                message=f"Your '{budget.budget_name}' budget has exceeded its limit! Spent: {total_spent:.2f} / Limit: {budget.total_limit:.2f}",
                notification_type="budget_alert"
            )
            logger.info(f"Created budget EXCEEDED notification for user {instance.user_id} on budget {budget.id}")

        # Check if 80% warning (only if not already exceeded)
        elif spending_ratio >= WARNING_THRESHOLD:
            # Check if we already sent an 80% warning for this budget recently
            existing_warning = Notification.objects.filter(
                user=instance.user,
                notification_type="budget_warning",
                title__icontains=budget.budget_name,
                is_read=False
            ).exists()

            if not existing_warning:
                percentage = int(spending_ratio * 100)
                Notification.objects.create(
                    user=instance.user,
                    title="Budget Warning",
                    message=f"You've used {percentage}% of your '{budget.budget_name}' budget. Spent: {total_spent:.2f} / Limit: {budget.total_limit:.2f}",
                    notification_type="budget_warning"
                )
                logger.info(f"Created budget WARNING notification for user {instance.user_id} on budget {budget.id} at {percentage}%")

    except Budget.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error in check_budget_limit signal: {e}")

