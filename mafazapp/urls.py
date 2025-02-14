from django.urls import path
from mafazapp import views


urlpatterns = [
    path('userdashboard/', views.userdashboard, name='userdashboard'),

]