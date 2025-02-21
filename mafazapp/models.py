from django.db import models

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django_countries.fields import CountryField
from django.contrib.auth import get_user_model


STATUS_CHOICES = (
    ('PENDING', 'Pending Approval'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
)

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)   
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    country = CountryField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING') 
    is_approved = models.BooleanField(default=False)  
    created_at = models.DateTimeField(auto_now_add=True) 
    has_requested = models.BooleanField(default=False)

    def __str__(self):
        return self.username



User = get_user_model()

class PasswordResetRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    requested_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Reset Request - {self.user.username}"
