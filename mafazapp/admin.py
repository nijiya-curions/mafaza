from django.contrib import admin
from .models import CustomUser,PasswordResetRequest,UserProjectAssignment


# Register your models here.
admin.site.register(CustomUser)
admin.site.register(PasswordResetRequest)
admin.site.register(UserProjectAssignment)



