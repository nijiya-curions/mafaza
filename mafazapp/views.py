from django.shortcuts import render
from .forms import SignupForm

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .models import CustomUser
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.contrib import messages



from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import get_user_model


def home(request):
    return render(request,'home.html')



def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_approved = False  # New users will not be approved automatically
            user.save()
            # Redirect to the pending approval page or a confirmation page
            return redirect('pendingapproval')
    else:
        form = SignupForm()

    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:  # Check if user is already logged in
        # Redirect based on user type
        if request.user.is_superuser:
            return redirect('/pineapplepie/')  # Redirect superusers to Django admin
        elif request.user.is_staff:
            return redirect('admindashboard')  # Redirect staff to admin dashboard
        else:
            return redirect('userdashboard')  # Redirect normal users to user dashboard
        
    if request.method == 'POST':
        username_or_email = request.POST['username']
        password = request.POST['password']
        
        # Try to authenticate using username or email
        user = None
        if '@' in username_or_email:
            try:
                user = CustomUser.objects.get(email=username_or_email)
            except CustomUser.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=username_or_email, password=password)
        
        if user is not None and user.check_password(password):
            if not user.is_approved and not (user.is_superuser or user.is_staff):
                return render(request, 'pendingapproval.html', 
                    {'error': 'Your account is awaiting approval by an administrator.'})
            
            login(request, user)
            
            # Redirect based on user type
            if user.is_superuser:
                return redirect('/pineapplepie/')  # Django admin dashboard
            elif user.is_staff:
                return redirect('admindashboard')  # Admin dashboard
            else:
                return redirect('userdashboard')  # User dashboard
            
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'login.html')

# logout

def logout_view(request):
    logout(request)
    request.session.flush()  # Clear the session entirely
    return redirect('home')  # Redirect to login page


def pendingapproval(request):
    return render(request,'pendingapproval.html')

def user_required(user):
    return user.is_authenticated and not user.is_staff  # Ensures only non-admin users can access

user_login_required = user_passes_test(user_required, login_url='home')

# user dashboard
@never_cache
@user_login_required
def userdashboard(request):
    return render(request,'userdashboard.html')

# user transaction
@never_cache
@user_login_required
def usertransaction(request):
    return render(request,'usertransaction.html')

# user projects
@never_cache
@user_login_required
def userprojects(request):
    return render(request,'userprojects.html')

# admin side

# admin dashbaord
def admin_required(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(admin_required, login_url='home')
@never_cache
def admindashboard(request):
    return render(request,'admindashboard.html')


# admin users
def admin_required(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(admin_required, login_url='home')
@never_cache
def adminusers(request):
    User = get_user_model()

    # Get search query and user type filter
    search_query = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')

    # Base query: Exclude superusers
    users = User.objects.exclude(is_superuser=True)

    # Get only approved users
    approved_users = users.filter(is_approved=True)

    # Get only pending users
    pending_users = users.filter(is_approved=False)

    # Filter approved users by search query
    if search_query:
        approved_users = approved_users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Filter approved users by user type
    if user_type == 'Admin':
        approved_users = approved_users.filter(is_staff=True)
    elif user_type == 'User':
        approved_users = approved_users.filter(is_staff=False)

    # Sort approved users by first name
    approved_users = approved_users.order_by('first_name')

    # Paginate approved users
    paginator = Paginator(approved_users, 2)
    page_number = request.GET.get('page')
    page_users = paginator.get_page(page_number)

    # Handle User Activation / Deactivation & Role Change
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('adminusers')

        if request.user.is_staff:
            if action == 'confirm_toggle':  # Activate / Deactivate User
                user.is_approved = not user.is_approved
                user.save()
                status = "activated" if user.is_approved else "deactivated"
                messages.success(request, f"User {user.username} has been {status}.")
                return redirect('adminusers')

            elif action == 'promote':  # Promote to Admin (Staff)
                if not user.is_staff:
                    user.is_staff = True
                    user.save()
                    messages.success(request, f"User {user.username} has been promoted to Admin.")
                else:
                    messages.error(request, "User is already an Admin.")

            elif action == 'demote':  # Demote from Admin to Regular User
                if user.is_staff:
                    user.is_staff = False
                    user.save()
                    messages.success(request, f"User {user.username} has been demoted to a regular user.")
                else:
                    messages.error(request, "User is not an Admin.")

        else:
            messages.error(request, "You do not have permission to perform this action.")

    return render(request, 'adminusers.html', {
        'users': page_users,  # Paginated approved users
        'pending_users': pending_users,  # List of pending users
        'search_query': search_query,
        'user_type': user_type
    })

# def adminusers(request):
#     User = get_user_model()

#     # Get the search query from the GET request
#     search_query = request.GET.get('search', '')

#     # Filter users based on the search query
#     if search_query:
#         users = User.objects.exclude(is_superuser=True).filter(
#             first_name__icontains=search_query
#         ) | User.objects.exclude(is_superuser=True).filter(
#             last_name__icontains=search_query
#         )
#     else:
#         users = User.objects.exclude(is_superuser=True)

#     # Sort users: Show not activated (is_approved=False) first, then activated users
#     users = users.order_by('is_approved', 'first_name')

#     # Pagination: Show 10 users per page
#     paginator = Paginator(users, 10)
#     page_number = request.GET.get('page')
#     page_users = paginator.get_page(page_number)

#     if request.method == 'POST':
#         user_id = request.POST.get('user_id')
#         action = request.POST.get('action')

#         try:
#             user = User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             messages.error(request, "User not found.")
#             return redirect('adminusers')

#         # Only staff users can promote/demote other users
#         if request.user.is_staff:
#             if action == 'confirm_toggle':
#                 user.is_approved = not user.is_approved
#                 user.save()
#                 status = "activated" if user.is_approved else "deactivated"
#                 messages.success(request, f"User {user.username} has been {status}.")
#                 return redirect('adminusers')
#             elif action == 'promote':  # Promote to staff
#                 if not user.is_staff:
#                     user.is_staff = True
#                     user.save()
#                     messages.success(request, f"User {user.username} has been promoted to Staff.")
#                 else:
#                     messages.error(request, "User is already a Staff member.")
#             elif action == 'demote':  # Demote from staff
#                 if user.is_staff:
#                     user.is_staff = False
#                     user.save()
#                     messages.success(request, f"User {user.username} has been demoted to a regular user.")
#                 else:
#                     messages.error(request, "User is not a Staff member.")
#         else:
#             messages.error(request, "You do not have permission to perform this action.")
#             return redirect('adminusers')

#     return render(request, 'adminusers.html', {
#         'users': page_users,  # Paginated users
#         'search_query': search_query
#     })






   
























# admin transaction
def admin_required(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(admin_required, login_url='home')
@never_cache
def admintransaction(request):
    return render(request,'admintransaction.html')

# admin user ledger
def admin_required(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(admin_required, login_url='home')
@never_cache
def userledger(request):
    return render(request,'userledger.html')

# admin projects
def admin_required(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(admin_required, login_url='home')
@never_cache
def adminprojects(request):
    return render(request,'adminprojects.html')





    