import cloudinary.uploader
from django.db import models
from django.conf import settings

class UserRequest(models.Model):
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

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='user_requests')
    request_type = models.CharField(max_length=50, choices=REQUEST_TYPES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,default='raised')
    admin_comment = models.TextField(blank=True)
    user_comment = models.TextField(blank=True)
    document = models.URLField(blank=True,null=True)
    parent_request = models.ForeignKey('self', null=True, blank=True,on_delete=models.SET_NULL, related_name='reraises')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"REQ-{self.id} | {self.user.username} | {self.request_type} | {self.status}"
