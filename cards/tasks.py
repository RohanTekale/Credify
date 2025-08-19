from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import CreditCard
from credify_core.utils import is_user_inactive
from datetime import timedelta


User = get_user_model()

@shared_task
def auto_freeze_inactive_cards():
    """Freeze cards of users inactive for 7+ days."""
    seven_days_ago = timezone.now() - timedelta(days=7)
    inactive_users = User.objects.filter(
        last_login__lt=seven_days_ago, is_active=True
    )
    for user in inactive_users:
        if is_user_inactive(user, days=7):
            cards = CreditCard.objects.filter(user=user, status='active')
            for card in cards:
                card.status = 'frozen'
                card.updated_at = timezone.now()
                card.save()

                print(f"Froze Card {card.id} for user {user.username}")

@shared_task
def auto_block_inactive_or_deleted_cards():
    """Block cards of users inactive for 30+ days or deleted accounts."""
    thirty_days_ago = timezone.now() - timedelta(days=30)

    inactive_users = User.objects.filter(
        last_login__lt = thirty_days_ago, is_active=True
    )
    for user in inactive_users:
        if is_user_inactive(user,days=30):
            cards = CreditCard.objects.filter(user=user, status__in=['active', 'frozen'])
            for card in cards:
                card.status = 'blocked'
                card.updated_at = timezone.now()
                card.save()

                print(f"Blocked card {card.id} for user {user.username}")

    deleted_users = User.objects.filter(is_active=False)
    for user in deleted_users:
        cards = CreditCard.objects.filter(user=user, status__in=['active', 'frozen'])
        for card in cards:
            card.status = 'blocked'
            card.updated_at = timezone.now()
            card.save()
            print(f"Blocked card {card.id} for user {user.username}")  