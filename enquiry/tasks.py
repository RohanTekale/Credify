from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


@shared_task(bind=True, max_retries=3)
def send_request_status_email(self, user_email, request_id, request_type, new_status, admin_comment):
    try:
        friendly_type   = request_type.replace('_', ' ').title()
        friendly_status = new_status.replace('_', ' ').title()
 
        subject = f"[Credify] Your request {request_id} has been updated"
        message = (
            f"Hi,\n\n"
            f"Your request — {friendly_type} ({request_id}) — has been updated.\n\n"
            f"New status: {friendly_status}\n"
        )
        if admin_comment:
            message += f"\nAdmin comment:\n{admin_comment}\n"
 
        if new_status == 'rejected':
            message += (
                "\nYour request was rejected. You can log in to Credify and "
                "re-raise this request if needed.\n"
            )
        elif new_status == 'completed':
            message += (
                "\nYour request has been resolved. You can rate your experience "
                "by logging in to Credify.\n"
            )
 
        message += "\nThank you for using Credify."
 
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    
@shared_task(bind=True, max_retries=3)
def send_raised_request_reminder(self, user_email, request_id, request_type):
    """Reminder for requests sitting in 'raised' for 24+ hours."""
    try:
        friendly_type = request_type.replace('_', ' ').title()
        subject = f"[Credify] Your request {request_id} is being processed"
        message = (
            f"Hi,\n\n"
            f"Your request — {friendly_type} ({request_id}) — is still under review.\n\n"
            f"Our support team will update you as soon as possible.\n\n"
            f"Thank you for your patience."
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    
@shared_task
def check_sla_breaches():
    from .models import UserRequest
    breached= UserRequest.objects.filter(
        status__in =['raised','in_process'],
        sla_deadline__lt=timezone.now(),
        sla_breached = False,
    )
    count = breached.update(sla_breached=True)
    return f"Marked {count} requests as SLA breached."

@shared_task
def notify_stale_raised_requests():
    from .models import UserRequest

    cutoff = timezone.now() - timezone.timedelta(hours=24)
    stale = UserRequest.objects.filter(
        status = 'raised',
        created_at__lte=cutoff,
        reminder_sent=False
    ).select_related('user')
    sent_ids=[]
    for req in stale.iterator():
        send_raised_request_reminder.delay(
            req.user.email,
            f"REQ-{req.id}",
            req.request_type,
        )
        sent_ids.append(req.id)
    if sent_ids:
        UserRequest.objects.filter(id__in=sent_ids).update(reminder_sent=True)
    return f"Sent reminders for {len(sent_ids)} stale requests."
