from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from datetime import timedelta


class CardType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    default_credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=575.60)
    expiry_years = models.IntegerField(default=3)
    transaction_fee = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    requires_admin_approval = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class CreditCard(models.Model):
    CARD_STATUS = (
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('blocked', 'Blocked'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    card_type = models.ForeignKey(CardType, on_delete=models.PROTECT)
    card_number = models.CharField(max_length=256, unique=True)
    cvv = models.CharField(max_length=128)
    expiry_date = models.DateField()
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    available_credit = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=CARD_STATUS, default='active')
    nickname = models.CharField(max_length=50, blank=True)
    is_single_use = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['card_number']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.card_type.name} Card ending {self.card_number[-4:]} for {self.user.username}"


class CardRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    card_type = models.ForeignKey(CardType, on_delete=models.PROTECT)
    is_single_use = models.BooleanField(default=False)
    income = models.DecimalField(max_digits=10, decimal_places=2)
    occupation = models.CharField(max_length=100)
    intended_use = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card_type.name} request for {self.user.username}"
    
class Subscription(models.Model):
    SUBSCRIPTION_STATUS =(
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name='subscriptions')
    card_type = models.ForeignKey(CardType, on_delete=models.PROTECT)
    status = models.CharField(max_length=20,choices=SUBSCRIPTION_STATUS, default='active')
    is_limited_time = models.BooleanField(default=False)
    subscription_start = models.DateTimeField(auto_now_add=True)
    subscription_end= models.DateTimeField(null=True, blank=True)
    subscription_fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes= [
            models.Index(fields=['user']),
            models.Index(fields=['card']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.card_type.name} subscription for {self.user.username}"
    
    def save(self,*args, **kwargs):
        if self.is_limited_time and not self.subscription_end:
            self.subscription_end = self.subscription_start + timedelta(days=30)
        super().save(*args,**kwargs)


