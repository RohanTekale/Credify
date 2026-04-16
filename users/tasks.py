from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

@shared_task(bind=True,max_retries=3)
def send_verification_email(self,user_id):
    try:
        user = User.objects.get(id=user_id)
        token = str(RefreshToken.for_user(user).access_token)
        verification_link =f"http://localhost:3001/verify?token={token}"

        subject=f"Verify your email {user.username}"
        message=f"""Hi {user.username} please verify with below link {verification_link} to get access to the Most advnaced Financial Hub,If you didn’t register, ignore this email."""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        raise self.retry(exc=e, countdown=60)
   
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
