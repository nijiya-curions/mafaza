from django.contrib import admin
from .models import CustomUser,PasswordResetRequest


# Register your models here.
admin.site.register(CustomUser)
admin.site.register(PasswordResetRequest)



