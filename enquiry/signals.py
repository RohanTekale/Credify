from django.db.models.signals import post_save,pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import UserRequest,EnquiryStatusLog



@receiver(pre_save,sender=UserRequest)
def capture_old_status(sender,instance,**kwargs):
    if not instance.pk:
        instance._old_status=None
        return
    instance._old_status = (UserRequest.all_objects.filter(pk=instance.pk).values_list('status',flat=True).first())
   

@receiver(post_save,sender=UserRequest)
def on_request_saved(sender,instance,created,**kwargs):
    updated_fields = kwargs.get('update_fields')
    if updated_fields and 'status' not in updated_fields:
        return
    old_status = getattr(instance, '_old_status',None)
    if created:
        EnquiryStatusLog.objects.create(enquiry=instance,changed_by=instance.user,old_status=None,new_status=instance.status,comment="Request raised .",)
        return
    if old_status==instance.status:
        return
    
    EnquiryStatusLog.objects.create(enquiry=instance,changed_by=None,old_status=old_status,new_status=instance.status,comment='',)

    if instance.status in ('completed','rejected') and not instance.resolved_at:
        UserRequest.all_objects.filter(pk=instance.pk).update(resolved_at=timezone.now())
    if instance.is_viewed_by_user:
        UserRequest.all_objects.filter(pk=instance.pk).update(is_viewed_by_user=False)