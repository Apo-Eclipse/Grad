import logging
from decimal import Decimal
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.functions import Coalesce

from core.models import Transaction, Notification, Budget

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Transaction)
def check_budget_limit(sender, instance, created, **kwargs):
    """
    Signal to check if a budget limit is exceeded after a transaction is saved.
    """
    if not instance.budget_id:
        return

    try:
        budget = Budget.objects.get(id=instance.budget_id)
        
        # Calculate total spent for this budget
        # We perform the sum again to be accurate including the new transaction
        total_spent = Transaction.objects.filter(
            budget_id=budget.id, 
            active=True
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'))
        )['total']

        if total_spent >= budget.total_limit:
            # Check if we already notified recently? 
            # For simplicity, we notify every time the limit is exceeded by a new transaction.
            # A more complex system might curb duplicate alerts, but per requirements:
            
            Notification.objects.create(
                user=instance.user,
                title="Budget Limit Exceeded",
                message=f"Your '{budget.budget_name}' budget has exceeded its limit! Spent: {total_spent:.2f} / Limit: {budget.total_limit:.2f}",
                notification_type="budget_alert"
            )
            logger.info(f"Created budget notification for user {instance.user_id} on budget {budget.id}")

    except Budget.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error in check_budget_limit signal: {e}")
