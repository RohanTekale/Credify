from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from sentry_sdk import capture_exception


User = get_user_model()

@shared_task
def notify_admin_card_approve(card_request_id, user_id):
    pass