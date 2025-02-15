from django.urls import path
from mafazapp import views


urlpatterns = [
    path('userdashboard/', views.userdashboard, name='userdashboard'),
    path('usertransaction/', views.usertransaction, name='usertransaction'),
    path('userprojects/', views.userprojects, name='userprojects'),


]