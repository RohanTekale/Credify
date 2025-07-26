from celery import shared_task

@shared_task
def send_verification_email(user_id):
    # Placeholder for SendGrid email verification
    pass