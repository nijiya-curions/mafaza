from django.shortcuts import render

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.db.models import Q

from .models import PasswordResetRequest
from django.contrib.auth.hashers import make_password

from .forms import SignupForm,InvestmentProjectForm,UserTransactionForm,UserProfileUpdateForm,ForgotPasswordForm,TransactionForm
from .models import InvestmentProject,PasswordResetRequest,CustomUser
from django.utils.timezone import now


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
    request.session.flush()
    response = redirect('home')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def pendingapproval(request):
    return render(request,'pendingapproval.html')



def user_required(user):
    return user.is_authenticated and not user.is_staff
user_login_required = user_passes_test(user_required, login_url='home')


def admin_required(user):
    return user.is_authenticated and user.is_staff



# user dashboard

@login_required
@user_login_required
def userdashboard(request):
    user = request.user  # Get the logged-in user
    form = UserProfileUpdateForm(instance=user)

    if request.method == "POST":
        form = UserProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            updated_user = form.save(commit=False)  # Don't commit yet

            # Check if username, email, or password was changed
            username_changed = updated_user.username != user.username
            email_changed = updated_user.email != user.email
            password_changed = form.cleaned_data.get("password") != ""

            updated_user.save()  # Now save the changes

            # If username, email, or password changed, re-authenticate the user
            if username_changed or email_changed or password_changed:
                user = authenticate(
                    request, username=updated_user.username, password=form.cleaned_data.get("password") or user.password
                )
                if user:
                    login(request, user)  # Log them in with updated credentials
                    messages.success(request, "Profile updated! Please log in again.")
                    return redirect("login")  # Redirect to login page for security

            messages.success(request, "Profile updated successfully!")
            return redirect("userdashboard")  # Refresh the page

    return render(request, "userdashboard.html", {"form": form})


# user transaction
@never_cache
@user_login_required
def usertransaction(request):
    if request.method == "POST":
        form = UserTransactionForm(request.POST, request.FILES)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user  # Assign the logged-in user
            transaction.save()
            messages.success(request, "Transaction added successfully")
            return redirect("usertransaction")
        else:
            messages.error(request, "Error adding transaction")
    else:
        form = UserTransactionForm()

    context = {
        "form": form,  # Ensure form is always passed
        "today_date": now().strftime("%d %b %Y"),
        "projects": InvestmentProject.objects.all(),
    }

    return render(request, "usertransaction.html", context)


# user projects
@never_cache
@user_login_required
def userprojects(request):
    return render(request,'userprojects.html')

# admin side

# admin dashbaord

@user_passes_test(admin_required, login_url='home')
@never_cache
def admindashboard(request):
    user = request.user  # Get the logged-in admin
    if request.method == "POST" and "update_profile" in request.POST:
        form = UserProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admindashboard')  # Redirect after successful update
    else:
        form = UserProfileUpdateForm(instance=user)

    return render(request, 'admindashboard.html', {'form': form})


# admin users
@user_passes_test(admin_required, login_url='home')
@never_cache
def adminusers(request):
    User = get_user_model()

    search_query = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')
    users = User.objects.exclude(is_superuser=True)

    approved_users = users.filter(is_approved=True)

    pending_users = users.filter(is_approved=False)

    requested_users = approved_users.filter(has_requested=True)
    paginator = Paginator(approved_users, 2)
    page_number = request.GET.get('page')
    page_users = paginator.get_page(page_number)

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
                user.is_staff = True
                user.save()
                messages.success(request, f"User {user.username} has been promoted to Admin.")

            elif action == 'demote':  # Demote from Admin to Regular User
                user.is_staff = False
                user.save()
                messages.success(request, f"User {user.username} has been demoted to a regular user.")

            elif action == 'reset_password':  # Admin sets a new password
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')

                if new_password and new_password == confirm_password:
                    user.set_password(new_password)
                    user.has_requested = False  # Mark request as handled
                    user.save()

                    messages.success(request, f"Password for {user.username} has been reset successfully.")
                else:
                    messages.error(request, "Passwords do not match.")

                return redirect('adminusers')

        else:
            messages.error(request, "You do not have permission to perform this action.")

    return render(request, 'adminusers.html', {
        'users': page_users,
        'pending_users': pending_users,
        'requested_users': requested_users,
        'search_query': search_query,
        'user_type': user_type
    })

# admin transaction

@user_passes_test(admin_required, login_url='home')
@never_cache
def admintransaction(request):
    if request.method == "POST":
        form = TransactionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Transaction added successfully")
            return redirect("admintransaction")
        else:
            messages.error(request, "Error adding transaction")
    else:
        form = TransactionForm()

    # Fetching projects
    projects = InvestmentProject.objects.all()
    print("Projects:", projects) 

    context = {
        "form": form,
        "today_date": now().strftime("%d %b %Y"),
        "users": User.objects.all(),
        "projects": projects,
    }

    return render(request, "admintransaction.html", context)

# admin user ledger

@user_passes_test(admin_required, login_url='home')
@never_cache
def userledger(request):
    return render(request,'userledger.html')

# admin projects
@user_passes_test(admin_required, login_url='home')
@never_cache
def adminprojects(request):
    if request.method == "POST":
        form = InvestmentProjectForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('adminprojects')  # Refresh page after submission
    else:
        form = InvestmentProjectForm()

    projects = InvestmentProject.objects.all()  # Fetch existing projects
    return render(request, 'adminprojects.html', {'form': form, 'projects': projects})
# forgot password

User = get_user_model()

def forgot_password(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email_or_username = form.cleaned_data["email_or_username"]
            user = User.objects.filter(email=email_or_username).first() or User.objects.filter(username=email_or_username).first()

            if user:
                # Create the password reset request
                PasswordResetRequest.objects.create(user=user)

                # Ensure has_requested is updated
                user.has_requested = True
                user.save()

                messages.success(request, "Password reset request sent. An admin will review it.")
                return redirect("login")
    else:
        form = ForgotPasswordForm()

    return render(request, "forgot_password.html", {"form": form})

    