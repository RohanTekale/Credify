from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_request_status_email(user_email, request_id, request_type, new_status, admin_comment):
    subject = f"Update on Your Request {request_id} has been Updated"
    message = (
        f"Your request ({request_type.replace('_', ' ').title()})"
        f"has been updated to: {new_status.upper()}.\n\n"
    )
    if admin_comment:
        message += f"Admin comment: {admin_comment}\n\n"
    if new_status == 'rejected':
        message += "Unfortunately, your request has been rejected.  or You can log in and re-raise this request if you need to. Please contact support for more details.\n"
    message += "Thank you for using Credify!"
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )
    
