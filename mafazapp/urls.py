from django.urls import path
from mafazapp import views
from uuid import UUID  # Import UUID if needed

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('signup/', views.signup, name='signup'),
     path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('pendingapproval/', views.pendingapproval, name='pendingapproval'),
    path('userdashboard/', views.userdashboard, name='userdashboard'),
    path('usertransaction/', views.usertransaction, name='usertransaction'),
    path('userprojects/', views.userprojects, name='userprojects'),
    path('admindashboard/', views.admindashboard, name='admindashboard'),
    path('adminusers/', views.adminusers, name='adminusers'),
    path('admintransaction/', views.admintransaction, name='admintransaction'),
    path('userledger/', views.userledger, name='userledger'),
    path('adminprojects/', views.adminprojects, name='adminprojects'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    # path('assign-project/', views.assign_project, name='assign_project'),
    path('documents/', views.document_list, name='document_list'),
    path('delete-document/<int:document_id>/', views.delete_document, name='delete_document'),


# 
    path('admin/users/<uuid:user_id>/documents/', views.admin_user_documents, name='admin_user_documents'),
    path('admin/users/documents/delete/<int:document_id>/', views.admin_delete_document, name='admin_delete_document'),


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)