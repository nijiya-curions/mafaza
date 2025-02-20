from django.shortcuts import render
from .forms import SignupForm

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .models import CustomUser
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import user_passes_test


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
    return render(request,'adminusers.html')

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





    