from django.db import models

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


STATUS_CHOICES = (
    ('PENDING', 'Pending Approval'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
)

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)   
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    country = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING') 
    is_approved = models.BooleanField(default=False)  
    created_at = models.DateTimeField(auto_now_add=True) 
    
    def __str__(self):
        return self.username
