from django.contrib.auth .models import AbstractUser
from django.db import models

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
    is_support = models.BooleanField(default=False)  # this is for support staf


    def __str__(self):
        return self.username


    