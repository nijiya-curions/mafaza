from django.urls import path
from mafazapp import views


urlpatterns = [
    path('userdashboard/', views.userdashboard, name='userdashboard'),
    path('usertransaction/', views.usertransaction, name='usertransaction'),
    path('userprojects/', views.userprojects, name='userprojects'),
    path('admindashboard/', views.admindashboard, name='admindashboard'),
    path('adminusers/', views.adminusers, name='adminusers'),
    path('admintransaction/', views.admintransaction, name='admintransaction'),
    path('userledger/', views.userledger, name='userledger'),
    path('adminprojects/', views.adminprojects, name='adminprojects'),



]