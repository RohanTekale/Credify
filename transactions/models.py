from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from cards.models import CreditCard


class Transaction(models.Model):
    TRANSACTION_STATUS = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    fee = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        indexes = [
            models.Index(fields=['card', 'created_at']),
            
        ]
    

    def __str__(self):
        return f"Transaction of {self.amount} on {self.card} ({self.status})"

