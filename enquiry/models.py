from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.validators import MinValueValidator, MaxValueValidator



REQUEST_TYPES = [
    # Card
    ('credit_limit_increase',   'Credit Limit Increase'),
    ('credit_limit_decrease',   'Credit Limit Decrease'),
    ('card_upgrade',            'Card Upgrade'),
    ('card_downgrade',          'Card Downgrade'),
    ('card_replacement',        'Card Replacement'),
    ('card_cancellation',       'Card Cancellation'),
    ('single_use_card_request', 'Single-Use Card Request'),
    ('card_unfreeze',           'Card Unfreeze Request'),
    # Transaction
    ('transaction_dispute',     'Transaction Dispute'),
    ('refund_request',          'Refund Request'),
    ('transaction_clarification','Transaction Clarification'),
    ('failed_transaction',      'Failed Transaction Report'),
    # Account
    ('kyc_re_submission',       'KYC Re-submission Request'),
    ('account_reactivation',    'Account Reactivation'),
    ('profile_update_request',  'Profile Update Request'),
    ('account_closure',         'Account Closure'),
    # Billing
    ('subscription_cancellation','Subscription Cancellation'),
    ('subscription_upgrade',    'Subscription Upgrade'),
    ('billing_dispute',         'Billing Dispute'),
    ('fee_waiver',              'Fee Waiver Request'),
    # Security
    ('suspected_fraud',         'Suspected Fraud Report'),
    ('pin_reset',               'PIN / Security Reset'),
    # Other
    ('other',                   'Other'),
]
STATUS_CHOICES = [
    ('raised', 'Raised'),
    ('in_process', 'In Process'),
    ('completed', 'Completed'),
    ('rejected', 'Rejected'),
]

PRIORITY_CHOICES = [
    ('low',    'Low'),
    ('normal', 'Normal'),
    ('high',   'High'),
    ('urgent', 'Urgent'),
]

SLA_HOURS = {
    'low':    72,
    'normal': 48,
    'high':   24,
    'urgent': 4,
}

class ActiveEnquiryManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class UserRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='user_requests')
    request_type = models.CharField(max_length=50, choices=REQUEST_TYPES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,default='raised')
    priority = models.CharField(max_length=10,choices=PRIORITY_CHOICES,default='normal')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL, null=True,blank=True, related_name='assigned_requests')
    assigned_at = models.DateTimeField(null=True,blank=True)
    document = models.URLField(blank=True,null=True)
    sla_deadline = models.DateTimeField(null=True,blank=True)
    sla_breached = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True,blank=True)
    user_rating = models.PositiveSmallIntegerField(null=True,blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    user_feedback = models.TextField(blank=True)
    is_viewed_by_user = models.BooleanField(default=False)
    parent_request = models.ForeignKey('self', null=True, blank=True,on_delete=models.SET_NULL, related_name='reraises')
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True,blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reminder_sent=models.BooleanField(default=False)
    objects  = ActiveEnquiryManager()
    all_objects = models.Manager()


    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['request_type']),
            models.Index(fields=['sla_breached']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"REQ-{self.id} | {self.user.username} | {self.request_type} | {self.status}"
    
    def set_sla_deadline(self):
        hours = SLA_HOURS.get(self.priority,48)
        self.sla_deadline = timezone.now() + timedelta(hours=hours)

    def save(self, *args, **kwargs):
        if not self.pk:  
            self.set_sla_deadline()
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted','deleted_at'])

    def mark_resolved(self):
        if not self.resolved_at:
            self.resolved_at =timezone.now()
            self.save(update_fields=['resolved_at'])

class EnquiryComment(models.Model):
    enquiry = models.ForeignKey(UserRequest, on_delete=models.CASCADE,related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL, null=True)
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        tag = 'internal' if self.is_internal else 'public'
        return f"comment [{tag}] on REQ-{self.enquiry.id} by {self.author}"
    
class EnquiryStatusLog(models.Model):
    enquiry = models.ForeignKey(UserRequest,on_delete=models.CASCADE, related_name='history')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    old_status = models.CharField(max_length=20,blank=True)
    new_status = models.CharField(max_length=20)
    comment = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['changed_at']
    
    def __str__(self):
        return f"REQ-{self.enquiry_id}: {self.old_status} → {self.new_status} at {self.changed_at}"



