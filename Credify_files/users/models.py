from django.contrib.auth .models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    kyc_document = models.URLField(blank=True, null=True)    #Cloudinary URL
    kyc_status = models.CharField(
        max_length=20, 
        choices=[('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')],
        default= 'pending'
    )
    is_email_verified = models.BooleanField(default=False)
    is_support = models.BooleanField(default=False)  # this is for support staff

    income = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
        help_text="Annual income in USD for credit limit evaluation"
    )


    def __str__(self):
        return self.username

class KYCReviewLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kyc_reviews')
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL,null=True, related_name='reviewed_kycs')
    kyc_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('verified', 'Verified'), ('rejectcommened', 'Rejected')])
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"KYC Review for {self.user.username} by {self.reviewer.username} - {self.kyc_status}"
    
class ReactivationRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reactivation_requests')
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20,choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    admin_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return 


    