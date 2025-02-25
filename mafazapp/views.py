from django.shortcuts import render

from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.contrib import messages

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from django.db.models import Q

from .models import PasswordResetRequest
from django.contrib.auth.hashers import make_password

from .forms import SignupForm,InvestmentProjectForm,UserTransactionForm,UserProfileUpdateForm,ForgotPasswordForm,TransactionForm,UserDocumentForm
from .models import InvestmentProject,PasswordResetRequest,CustomUser,UserDocument,UserProjectAssignment,Transaction
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
@user_login_required
@never_cache
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

    # **Transaction History**
    transactions = Transaction.objects.filter(user=user).order_by('-date')

    # **Calculations**
    total_investments = transactions.filter(transaction_type="investment", status="approved").aggregate(Sum("amount"))["amount__sum"] or 0
    total_withdrawals = transactions.filter(transaction_type="withdrawal", status="approved").aggregate(Sum("amount"))["amount__sum"] or 0

    # **Calculate Total ROI as the sum of all assigned ROI values**
    user_projects = UserProjectAssignment.objects.filter(user=user)
    total_roi_percentage = sum(assignment.roi or 0 for assignment in user_projects)  # Sum of all user-assigned ROI percentages

    # **Convert ROI percentage to actual value**
    total_returns = (total_roi_percentage / 100) * total_investments if total_investments > 0 else 0

    # **Other calculations**
    cash_circulation = total_investments - total_withdrawals  # Simple cash flow calculation
    total_projects = InvestmentProject.objects.filter(transaction__user=user).distinct().count()

    context = {
        "form": form,
        "total_investments": total_investments,
        "total_returns": total_returns,  # Now converted from ROI percentage to actual value
        "cash_circulation": cash_circulation,
        "total_roi": total_roi_percentage,  # ROI in percentage
        "total_projects": total_projects,
        "total_withdrawals": total_withdrawals,
        "transactions": transactions,
    }

    return render(request, "userdashboard.html", context)

# user transaction 

@user_login_required
@never_cache
def usertransaction(request):
    if request.method == "POST":
        form = UserTransactionForm(request.POST, request.FILES)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user  # Assign the logged-in user
            transaction.save()
            messages.success(request, "Transaction added successfully!")
            return redirect("usertransaction")  # Redirect to the same page
        else:
            messages.error(request, "Error adding transaction. Please check the form.")
    else:
        form = UserTransactionForm()

    projects = InvestmentProject.objects.all()  # Fetch available projects
    transactions_list = Transaction.objects.filter(user=request.user).order_by('-date') 
    paginator = Paginator(transactions_list, 5)  
    page = request.GET.get("page")

    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    context = {
        "form": form,
        "projects": projects,
        "transactions": transactions,
        "today_date": now().strftime("%d %b %Y"),
    }
    return render(request, "usertransaction.html", context)

# admin side

 # user projects
@never_cache
@user_login_required
def userprojects(request):
    return render(request,'userprojects.html')


# admin dashbaord
from django.db.models import Sum, Count, Q

@user_passes_test(admin_required, login_url='home')
@never_cache
def admindashboard(request):
    user = request.user  

    if request.method == "POST" and "update_profile" in request.POST:
        form = UserProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("admindashboard")
    else:
        form = UserProfileUpdateForm(instance=user)

    total_investments = Transaction.objects.filter(transaction_type="investment", status="approved").aggregate(Sum("amount"))["amount__sum"] or 0
    total_returns = Transaction.objects.filter(transaction_type="return", status="approved").aggregate(Sum("amount"))["amount__sum"] or 0
    total_withdrawals = Transaction.objects.filter(transaction_type="withdrawal").aggregate(Sum("amount"))["amount__sum"] or 0
    cash_circulation = total_investments - total_withdrawals  

    active_users = User.objects.filter(is_active=True).count()
    total_projects = InvestmentProject.objects.count()  

    # Fetch all transactions to display in the table with pagination
    transactions_list = Transaction.objects.select_related("user", "project").order_by("-date")
    paginator = Paginator(transactions_list, 5)  # Show 10 transactions per page
    page = request.GET.get("page")

    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    context = {
        "form": form,
        "total_investments": total_investments,
        "total_returns": total_returns,
        "cash_circulation": cash_circulation,
        "active_users": active_users,
        "total_projects": total_projects,
        "total_withdrawals": total_withdrawals,
        "transactions": transactions,  # Paginated transactions
    }

    return render(request, "admindashboard.html", context)

 
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

    projects = InvestmentProject.objects.all()  # Get all projects

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('adminusers')

        if request.user.is_staff:
            if action == 'confirm_toggle':
                user.is_approved = not user.is_approved
                user.save()
                status = "activated" if user.is_approved else "deactivated"
                messages.success(request, f"User {user.username} has been {status}.")
                return redirect('adminusers')

            elif action == 'promote':
                user.is_staff = True
                user.save()
                messages.success(request, f"User {user.username} has been promoted to Admin.")

            elif action == 'demote':
                user.is_staff = False
                user.save()
                messages.success(request, f"User {user.username} has been demoted to a regular user.")

            elif action == 'reset_password':
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')

                if new_password and new_password == confirm_password:
                    user.set_password(new_password)
                    user.has_requested = False
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
        'user_type': user_type,
        'projects': projects  # Pass the projects to the template
    })


# admin transaction

def admin_required(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(admin_required, login_url='login')
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

    # Fetching projects and pending transactions
    projects = InvestmentProject.objects.all()
    pending_transactions = Transaction.objects.filter(status="pending").order_by('-date')

    context = {
        "form": form,
        "today_date": now().strftime("%d %b %Y"),
        "users": User.objects.all(),
        "projects": projects,
        "transactions": pending_transactions,  # Include pending transactions
    }

    return render(request, "admintransaction.html", context)

@user_passes_test(admin_required, login_url='login')
@never_cache
def approve_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)
    transaction.status = 'approved'
    transaction.save()
    messages.success(request, f"Transaction {transaction_id} approved successfully.")
    return redirect("admintransaction")  # Redirect back to the admin dashboard

@user_passes_test(admin_required, login_url='login')
@never_cache
def reject_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)
    transaction.status = 'rejected'
    transaction.save()
    messages.error(request, f"Transaction {transaction_id} rejected.")
    return redirect("admintransaction")  # Redirect back to the admin dashboard

# admin user ledger

@user_passes_test(admin_required, login_url='home')
@never_cache
def userledger(request):
    transactions_list = Transaction.objects.all().select_related("user", "project").order_by('-date')
    
    # Pagination
    paginator = Paginator(transactions_list, 5)  
    page = request.GET.get("page")

    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    context = {
        "transactions": transactions,
    }
    return render(request, "userledger.html", context)

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

    

# document for admin

@user_passes_test(admin_required, login_url='home')
@never_cache
def admin_user_documents(request, user_id):
    User = get_user_model()
    """Admin can view and download documents uploaded by a user."""
    user = get_object_or_404(User, id=user_id)
    documents = UserDocument.objects.filter(user=user)

    return render(request, 'admin_user_documents.html', {'user': user, 'documents': documents})


@user_passes_test(admin_required, login_url='home')
@never_cache
def admin_delete_document(request, document_id):
    """Admin can delete a user's document."""
    document = get_object_or_404(UserDocument, id=document_id)
    document.file.delete()  # Deletes the file from storage
    document.delete()
    messages.success(request, "Document deleted successfully.")
    return redirect('admin_user_documents', user_id=document.user.id)




# document section for users


def document_list(request):
    """List all documents and handle document uploads and edits in the same view."""
    documents = UserDocument.objects.filter(user=request.user)
    form = UserDocumentForm()
    edit_form = None
    document_to_edit = None

    if request.method == 'POST':
        # Check if it's an edit request
        document_id = request.POST.get('edit_document_id')

        if document_id:
            document_to_edit = get_object_or_404(UserDocument, id=document_id, user=request.user)
            edit_form = UserDocumentForm(request.POST, request.FILES, instance=document_to_edit)

            if edit_form.is_valid():
                edit_form.save()
                return redirect('document_list')  # Redirect after edit

        else:
            # This is a new document upload
            form = UserDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                document = form.save(commit=False)
                document.user = request.user
                document.save()
                return redirect('document_list')  # Redirect after upload

    # Handle edit request (GET request for edit form)
    document_id = request.GET.get('edit')
    if document_id:
        document_to_edit = get_object_or_404(UserDocument, id=document_id, user=request.user)
        edit_form = UserDocumentForm(instance=document_to_edit)

    return render(request, 'document_list.html', {
        'documents': documents,
        'form': form,
        'edit_form': edit_form,
        'document_to_edit': document_to_edit
    })


def delete_document(request, document_id):
    """Allow users to delete their uploaded documents."""
    document = get_object_or_404(UserDocument, id=document_id, user=request.user)
    document.file.delete()  # Delete the actual file from storage
    document.delete()
    return redirect('document_list')


# assigning
from django.contrib.auth.decorators import login_required, user_passes_test
@user_passes_test(admin_required, login_url='home')
@never_cache
def assign_project(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        project_id = request.POST.get('project_id')
        roi = request.POST.get('roi')

        User = get_user_model()
        user = get_object_or_404(User, id=user_id)  # Get the selected user
        project = get_object_or_404(InvestmentProject, id=project_id)  # Get the selected project

        # Assign project to the user
        assignment, created = UserProjectAssignment.objects.get_or_create(user=user, project=project)
        assignment.roi = roi  # Update ROI
        assignment.save()

        messages.success(request, f"Project {project.project_name} assigned to {user.username} with ROI {roi}.")
        return redirect('adminusers')  # Redirect to admin dashboard or assigned projects page

    return redirect('adminusers')  

@user_passes_test(admin_required, login_url='home')
@never_cache
def assigned_projects(request):
    User = get_user_model()
    assigned_projects = UserProjectAssignment.objects.filter(user=request.user)
    if not assigned_projects:
        assigned_projects = UserProjectAssignment.objects.filter(user=User.objects.first())  # Test with first user
    return render(request, 'adminusers.html', {'assigned_projects': assigned_projects})




 