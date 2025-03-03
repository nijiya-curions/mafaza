from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser
from django_countries.fields import CountryField
from django.contrib.auth import get_user_model
from django.conf import settings


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



class InvestmentProject(models.Model):
    project_name = models.CharField(max_length=255)
    total_investment = models.DecimalField(max_digits=15, decimal_places=2)
    min_roi = models.DecimalField(max_digits=5, decimal_places=2, help_text="Minimum Return on Investment (%)")
    max_roi = models.DecimalField(max_digits=5, decimal_places=2, help_text="Maximum Return on Investment (%)")
    project_description = models.TextField()
    image1 = models.ImageField(upload_to='project_images/', blank=True, null=True)
    image2 = models.ImageField(upload_to='project_images/', blank=True, null=True)
    image3 = models.ImageField(upload_to='project_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)  # Added active/inactive toggle
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.project_name 
   

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('investment', 'Investment'),
        ('withdrawal', 'Withdrawal'),
    ]

    date = models.DateField(auto_now_add=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="transactions") 
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    project = models.ForeignKey(InvestmentProject, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    narration = models.TextField()
    receipt = models.ImageField(upload_to='receipts/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')  

    def __str__(self):
        return f"{self.user} - {self.transaction_type} - {self.amount}"


User = get_user_model()

class UserProjectAssignment(models.Model):
    
    RETURN_PERIOD_CHOICES = [

        ('5m', '5 Minutes'),
        ('10m', '10 Minutes'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semiannual', 'Semiannual'),
        ('annual', 'Annual'),

    ]
      
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    project = models.ForeignKey('InvestmentProject', on_delete=models.CASCADE, related_name='assigned_users')
    roi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Custom ROI")
    return_period = models.CharField(max_length=20, choices=RETURN_PERIOD_CHOICES, default='5m')  # New field

    def get_effective_return(self):
        """ Return the assigned ROI or default to project's ROI. """
        if self.roi is not None:
            return self.roi
        return (
            self.project.fixed_return_percentage
            if hasattr(self.project, 'return_type') and self.project.return_type == 'fixed'
            else getattr(self.project, 'min_return_percentage', None)
        )
 
    def __str__(self):
        return f"{self.user.username} - {self.project.project_name} ({self.get_effective_return()}%) - {self.get_return_period_display()}"
 
   
# user document
class UserDocument(models.Model):
    DOCUMENT_TYPES = [
        ('aadhaar', 'Aadhaar Card'),
        ('voter_id', 'Voter ID'),
        ('passbook', 'Passbook'),
        ('other', 'Other')
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='user_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_document_type_display()}"


 