from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_verification_email(user_id):
    # Placeholder for SendGrid email verification
    pass

@shared_task
def send_kyc_notification_email(user_email, kyc_status, reviewer_comments):
    subject = f"KYC Status Update: {kyc_status.capitalize()}"
    message = f"Your KYC status has been updated to {kyc_status}."
    if reviewer_comments:
        message += f" Reviewer comments: {reviewer_comments}"
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )
@shared_task
def send_reactivation_notification_email(user_email, status, admin_comments):
    subject = f"Account Reactivation Request: {status.capitalize()}"
    message = f"Your account reactivation request has been {status}."
    if admin_comments:
        message += f"\nAdmin Comments: {admin_comments}"
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )
