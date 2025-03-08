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
from .forms import SignupForm,InvestmentProjectForm,UserTransactionForm,UserProfileUpdateForm,ForgotPasswordForm,TransactionForm,UserDocumentForm,UserProjectAssignmentForm
from .models import InvestmentProject,PasswordResetRequest,CustomUser,UserDocument,UserProjectAssignment,Transaction
from django.utils.timezone import now

def home(request):
    projects = InvestmentProject.objects.all()

    context = {
        "projects": projects, 
    }
    return render(request, "home.html", context)


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
    user = request.user  
    form = UserProfileUpdateForm(instance=user)

    if request.method == "POST":
        form = UserProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            updated_user = form.save(commit=False)
            updated_user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("userdashboard")

    # **Search Functionality**
    search_query = request.GET.get("search", "").strip()
    all_transactions = Transaction.objects.filter(user=user).order_by("date")  

    if search_query:
        all_transactions = all_transactions.filter(
            Q(project__project_name__icontains=search_query) |
            Q(narration__icontains=search_query) |
            Q(transaction_type__icontains=search_query) |
            Q(amount__icontains=search_query)
        )

    # **Apply Pagination**
    paginator = Paginator(all_transactions, 10)  # Show 10 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)  

    # **Calculations**
    total_investments = all_transactions.filter(transaction_type="investment", status="approved").aggregate(Sum("amount"))["amount__sum"] or 0
    total_withdrawals = all_transactions.filter(transaction_type="withdrawal", status="approved").aggregate(Sum("amount"))["amount__sum"] or 0

    user_projects = UserProjectAssignment.objects.filter(user=user)
    total_projects = user_projects.count()  
    
    total_roi_percentage = sum(assignment.roi or 0 for assignment in user_projects)

    total_returns = (total_roi_percentage / 100) * total_investments if total_investments > 0 else 0
    cash_circulation = total_investments - total_withdrawals

    # **Compute Returns & Running Balance**
    running_balance = 0  
    for transaction in page_obj:  # Process only paginated transactions
        transaction.returns = (total_roi_percentage / 100) * transaction.amount if transaction.transaction_type == "investment" else 0
        if transaction.transaction_type == "investment":
            running_balance += transaction.amount
        elif transaction.transaction_type == "withdrawal":
            running_balance -= transaction.amount
        transaction.balance = running_balance  

    context = {
        "form": form,
        "total_investments": total_investments,
        "total_returns": total_returns,
        "cash_circulation": cash_circulation,
        "total_roi": total_roi_percentage,
        "total_projects": total_projects, 
        "total_withdrawals": total_withdrawals,
        "transactions": page_obj,  
        "search_query": search_query,  
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

    # Fetch only assigned projects for the logged-in user
    assigned_projects = UserProjectAssignment.objects.filter(user=request.user).select_related("project")

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
        "projects": [assignment.project for assignment in assigned_projects],  # Pass only assigned projects
        "transactions": transactions,
        "today_date": now().strftime("%d %b %Y"),
    }
    return render(request, "usertransaction.html", context)


# admin side

 # user projects
@never_cache
@user_login_required
def userprojects(request):
    user = request.user  

    assigned_projects = UserProjectAssignment.objects.filter(user=user).select_related("project")

    mafaza_projects = InvestmentProject.objects.filter(is_active=True)

    paginator = Paginator(mafaza_projects, 8) 
    page_number = request.GET.get("page")
    mafaza_page_obj = paginator.get_page(page_number)  

    context = {
        "assigned_projects": assigned_projects,
        "mafaza_projects": mafaza_page_obj, 
    }

    return render(request, "userprojects.html", context)

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

    active_users = get_user_model().objects.filter(is_active=True).count()
    total_projects = InvestmentProject.objects.count()  

    # Handle search query
    search_query = request.GET.get("search", "")
    if search_query:
        transactions_list = Transaction.objects.select_related("user", "project").filter(
            Q(user__username__icontains=search_query) |
            Q(project__project_name__icontains=search_query)
        ).order_by("-date")
    else:
        transactions_list = Transaction.objects.select_related("user", "project").filter(
            ~Q(status="pending")
        ).order_by("-date")

    paginator = Paginator(transactions_list, 5)  # Show 5 transactions per page
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
        "search_query": search_query,  # Pass the search query to the template
    }

    return render(request, "admindashboard.html", context)


# admin users
@user_passes_test(admin_required, login_url='home')
@never_cache
def adminusers(request):
    User = get_user_model()
    
    selected_user_id = request.GET.get("selected_user")
    selected_user = None
    assigned_projects = []

    if selected_user_id:
        try:
            selected_user = User.objects.get(id=selected_user_id)
            assigned_projects = UserProjectAssignment.objects.filter(user=selected_user)
        except User.DoesNotExist:
            messages.error(request, "Selected user not found.")
    search_query = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')
    users = User.objects.exclude(is_superuser=True)

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if user_type:
        if user_type == 'Admin':
            users = users.filter(is_staff=True)
        elif user_type == 'User':
            users = users.filter(is_staff=False)

    approved_users = users.filter(is_approved=True)
    pending_users = users.filter(is_approved=False)
    requested_users = approved_users.filter(has_requested=True)
    paginator = Paginator(approved_users, 2)
    page_number = request.GET.get('page')
    page_users = paginator.get_page(page_number)

    projects = InvestmentProject.objects.all()
    form = UserProjectAssignmentForm()

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
                  
            elif action == 'assign_project':  
                form = UserProjectAssignmentForm(request.POST)
                if form.is_valid():
                    assignment = form.save(commit=False)
                    assignment.user = user  # Assign selected user
                    assignment.save() 
                    messages.success(request, f"Project assigned to {user.username} successfully!")
                else:
                    messages.error(request, "Error assigning project. Please check the form.")

                return redirect('adminusers')
       
        else:
            messages.error(request, "You do not have permission to perform this action.")

    return render(request, 'adminusers.html', {
        'users': page_users,
        'pending_users': pending_users,
        'requested_users': requested_users,
        'search_query': search_query,
        'user_type': user_type,
        'projects': projects,
        'form': form,
'selected_user': selected_user,
        'assigned_projects': assigned_projects,
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

    # Get selected user ID from the request (if any)
    selected_user_id = request.GET.get("selected_user")

    if selected_user_id:
        try:
            selected_user = User.objects.get(id=selected_user_id)
            assigned_projects = UserProjectAssignment.objects.filter(user=selected_user).select_related("project")
            projects = [assignment.project for assignment in assigned_projects]
        except User.DoesNotExist:
            projects = InvestmentProject.objects.all()  # Fallback: all projects
    else:
        projects = InvestmentProject.objects.all()  # Default: all projects

    # Filtering transactions
    user_type = request.GET.get("user_type", "All")
    transactions_query = Transaction.objects.filter(status="pending").order_by('-date')

    if user_type == "Admin":
        transactions_query = transactions_query.filter(user__is_staff=True)
    elif user_type == "User":
        transactions_query = transactions_query.filter(user__is_staff=False)

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(transactions_query, 10)

    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    context = {
        "form": form,
        "today_date": now().strftime("%d %b %Y"),
        "users": User.objects.all(),
        "projects": projects,  # Pass the filtered projects
        "transactions": transactions,
        "user_type": user_type,
        "selected_user_id": selected_user_id,  # Pass selected user to template
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
def userledger(request, user_id=None):
    # Get filter type from request
    filter_type = request.GET.get("filter", "All")  # Default is "All"

    # Get distinct users with at least one transaction
    users_with_transactions = CustomUser.objects.filter(
        transactions__isnull=False
    ).distinct()

    # Apply filter using is_staff
    if filter_type == "Admin":
        users_with_transactions = users_with_transactions.filter(is_staff=True)  # Admins
    elif filter_type == "User":
        users_with_transactions = users_with_transactions.filter(is_staff=False)  # Normal users

    # Get only the latest transaction for each user
    latest_transactions = []
    for user in users_with_transactions:
        latest_transaction = (
            Transaction.objects.filter(user=user).order_by("-date").first()
        )
        if latest_transaction:
            latest_transactions.append(latest_transaction)

    # If user_id is provided, get all transactions for that user
    ledger_data = None
    selected_user = None
    if user_id:
        selected_user = get_object_or_404(CustomUser, id=user_id)
        ledger_data = Transaction.objects.filter(user=selected_user).order_by("date")

        # Calculate running balance and total withdrawal
        running_balance = 0
        total_withdrawal = 0
        for transaction in ledger_data:
            if transaction.transaction_type == "investment":
                running_balance += transaction.amount
            elif transaction.transaction_type == "withdrawal":
                running_balance -= transaction.amount
                total_withdrawal += transaction.amount  
            transaction.running_balance = running_balance  # Attach running balance to transaction

    # Paginate latest transactions (only one per user)
    paginator = Paginator(latest_transactions, 5)
    page_number = request.GET.get("page")
    transactions_page = paginator.get_page(page_number)

    return render(request, "userledger.html", {
        "transactions": transactions_page,
        "ledger_data": ledger_data,
        "selected_user": selected_user,
        "filter_type": filter_type,  # Pass filter type to template
    })





# def userledger(request):
#     transactions_list = Transaction.objects.all().select_related("user", "project").order_by('-date')
    
#     # Pagination
#     paginator = Paginator(transactions_list, 5)  
#     page = request.GET.get("page")

#     try:
#         transactions = paginator.page(page)
#     except PageNotAnInteger:
#         transactions = paginator.page(1)
#     except EmptyPage:
#         transactions = paginator.page(paginator.num_pages)

#     context = {
#         "transactions": transactions,
#     }
#     return render(request, "userledger.html", context)



# admin projects
from django.http import JsonResponse

@user_passes_test(admin_required, login_url='home')
@never_cache
def adminprojects(request):
    if request.method == "POST":
        project_id = request.POST.get('project_id')
        uploaded_images = request.FILES.getlist('images[]')  # Get all uploaded images

        if project_id:
            project = get_object_or_404(InvestmentProject, id=project_id)
            form = InvestmentProjectForm(request.POST, instance=project)
        else:
            form = InvestmentProjectForm(request.POST)

        if form.is_valid():
            project = form.save(commit=False)  # Do not save yet

            # Assign images manually
            if len(uploaded_images) > 0:
                project.image1 = uploaded_images[0]
            if len(uploaded_images) > 1:
                project.image2 = uploaded_images[1]
            if len(uploaded_images) > 2:
                project.image3 = uploaded_images[2]

            project.save()  # Save with images
            return redirect('adminprojects')

    else:
        form = InvestmentProjectForm()

    projects = InvestmentProject.objects.all()
    return render(request, 'adminprojects.html', {'form': form, 'projects': projects})

# Handle Active/Inactive Toggle
def toggle_project_status(request, project_id):
    project = get_object_or_404(InvestmentProject, id=project_id)
    project.is_active = not project.is_active
    project.save()
    return JsonResponse({'status': 'success', 'is_active': project.is_active})

def edit_project(request, project_id):
    project = get_object_or_404(InvestmentProject, id=project_id)

    if request.method == "POST":
        form = InvestmentProjectForm(request.POST, instance=project)
        uploaded_images = request.FILES.getlist('images[]')  # Get multiple uploaded images

        if form.is_valid():
            project = form.save(commit=False)  # Don't save yet

            # Assign images manually while keeping old ones if no new image is uploaded
            if len(uploaded_images) > 0:
                project.image1 = uploaded_images[0]  # First image
            if len(uploaded_images) > 1:
                project.image2 = uploaded_images[1]  # Second image
            if len(uploaded_images) > 2:
                project.image3 = uploaded_images[2]  # Third image
            
            project.save()  # Now save the project with updated images
            return redirect('project_list')

    else:
        form = InvestmentProjectForm(instance=project)

    return render(request, 'edit_project.html', {'form': form, 'project': project})

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

# delete document by admin

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


@user_login_required
def delete_document(request, document_id):
    """Allow users to delete their uploaded documents."""
    document = get_object_or_404(UserDocument, id=document_id, user=request.user)
    document.file.delete()  # Delete the actual file from storage
    document.delete()
    return redirect('document_list')

def delete_document(request, document_id):
    document = get_object_or_404(UserDocument, id = document_id, user= request.user)
    document.file.delete()
    document.delete()
    
# assigning

@user_passes_test(admin_required, login_url='home')
@never_cache
def assign_project(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        project_id = request.POST.get('project_id')
        roi = request.POST.get('roi')
        return_period = request.POST.get('return_period')

        User = get_user_model()
        user = get_object_or_404(User, id=user_id)  # Get the selected user
        project = get_object_or_404(InvestmentProject, id=project_id)  # Get the selected project

        # Assign project to the user
        assignment, created = UserProjectAssignment.objects.get_or_create(user=user, project=project)
        assignment.roi = roi  # Update ROI
        assignment.return_period = return_period  # Update return period
        assignment.save()

        messages.success(request, f"Project {project.project_name} assigned to {user.username} with ROI {roi}.")
        return redirect('adminusers')  # Redirect to admin dashboard or assigned projects page

    return redirect('adminusers')

@user_passes_test(admin_required, login_url='home')
@never_cache
def assigned_projects(request): 
    assigned_projects = UserProjectAssignment.objects.filter(user=request.user)
    projects = InvestmentProject.objects.all()  # Assuming you want to list all projects
      
    form = UserProjectAssignmentForm()  # Initialize the form

    return render(request, 'adminusers.html', {
        'assigned_projects': assigned_projects,
        'projects': projects,
        'form': form
    }) 
                       

# view for download admindashboard

import csv
from django.http import HttpResponse
from django.shortcuts import render
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.db.models import Q
from .models import Transaction  # Import your model


def export_transactions_csv(request):
    """Export Transactions as CSV (Excel) File"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(["DATE", "NAME", "PROJECT", "CREDIT", "DEBIT", "STATUS"])

    transactions = Transaction.objects.select_related("user", "project").filter(~Q(status="pending"))

    for transaction in transactions:
        writer.writerow([
            transaction.date.strftime("%d-%m-%Y"),
            transaction.user.get_full_name(),
            transaction.project.project_name,
            transaction.amount if transaction.transaction_type == "investment" else "-",
            transaction.amount if transaction.transaction_type == "withdrawal" else "-",
            transaction.status.upper()
        ])

    return response


def export_transactions_pdf(request):
    """Export Transactions as PDF File"""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="transactions.pdf"'

    # Create PDF
    pdf = canvas.Canvas(response, pagesize=letter)
    pdf.setTitle("Transactions Report")

    # Title
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 750, "Transactions Report")

    # Table Headers
    pdf.setFont("Helvetica-Bold", 10)
    headers = ["DATE", "NAME", "PROJECT", "CREDIT", "DEBIT", "STATUS"]
    x_offset = 50
    y_offset = 700

    for i, header in enumerate(headers):
        pdf.drawString(x_offset + (i * 90), y_offset, header)

    # Table Data
    pdf.setFont("Helvetica", 10)
    transactions = Transaction.objects.select_related("user", "project").filter(~Q(status="pending"))

    for index, transaction in enumerate(transactions):
        y_offset -= 20
        pdf.drawString(50, y_offset, transaction.date.strftime("%d-%m-%Y"))
        pdf.drawString(140, y_offset, transaction.user.get_full_name())
        pdf.drawString(230, y_offset, transaction.project.project_name)
        pdf.drawString(320, y_offset, str(transaction.amount) if transaction.transaction_type == "investment" else "-")
        pdf.drawString(410, y_offset, str(transaction.amount) if transaction.transaction_type == "withdrawal" else "-")
        pdf.drawString(500, y_offset, transaction.status.upper())

        # Prevent writing beyond the page
        if y_offset < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y_offset = 750

    pdf.save()
    return response


# userdashboard download
import io
from django.http import FileResponse
from django.contrib.auth.decorators import login_required
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.db.models import Sum
from .models import Transaction, UserProjectAssignment, InvestmentProject

@login_required
def download_transactions_pdf(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by("date")  # Oldest first for balance calculation

    # **Calculations**
    total_investments = transactions.filter(transaction_type="investment", status="approved").aggregate(Sum("amount"))["amount__sum"] or 0
    total_withdrawals = transactions.filter(transaction_type="withdrawal", status="approved").aggregate(Sum("amount"))["amount__sum"] or 0
    user_projects = UserProjectAssignment.objects.filter(user=user)
    total_roi_percentage = sum(assignment.roi or 0 for assignment in user_projects)
    total_returns = (total_roi_percentage / 100) * total_investments if total_investments > 0 else 0
    cash_circulation = total_investments - total_withdrawals
    total_projects = InvestmentProject.objects.filter(transaction__user=user).distinct().count()

    # **Generate PDF**
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # **Title**
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, height - 50, "Transaction Report")

    # **Table Headers**
    y_position = height - 100
    p.setFont("Helvetica-Bold", 10)
    headers = ["Date", "Project", "Narration", "Investment", "Returns", "Withdrawal", "Balance"]
    x_positions = [50, 120, 200, 320, 400, 470, 540]

    for i, header in enumerate(headers):
        p.drawString(x_positions[i], y_position, header)

    y_position -= 20
    p.setFont("Helvetica", 9)

    # **Balance Calculation**
    running_balance = 0

    for transaction in transactions:
        # **Compute Returns for Investments**
        calculated_return = (total_roi_percentage / 100) * transaction.amount if transaction.transaction_type == "investment" else 0

        # **Update Balance**
        if transaction.transaction_type == "investment":
            running_balance += transaction.amount
        elif transaction.transaction_type == "withdrawal":
            running_balance -= transaction.amount

        if y_position < 50:  # Add a new page if needed
            p.showPage()
            y_position = height - 50
            p.setFont("Helvetica-Bold", 10)
            for i, header in enumerate(headers):
                p.drawString(x_positions[i], y_position, header)
            y_position -= 20
            p.setFont("Helvetica", 9)

        p.drawString(x_positions[0], y_position, transaction.date.strftime("%d-%b-%Y"))
        p.drawString(x_positions[1], y_position, transaction.project.project_name)
        p.drawString(x_positions[2], y_position, transaction.narration)
        p.drawString(x_positions[3], y_position, str(transaction.amount) if transaction.transaction_type == "investment" else "-")
        p.drawString(x_positions[4], y_position, str(calculated_return) if calculated_return else "-")
        p.drawString(x_positions[5], y_position, str(transaction.amount) if transaction.transaction_type == "withdrawal" else "-")
        p.drawString(x_positions[6], y_position, str(running_balance))

        y_position -= 20

    # **Summary Section**
    y_position -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_position, f"Total Investments: {total_investments}")
    p.drawString(250, y_position, f"Total Returns: {total_returns}")
    p.drawString(450, y_position, f"Total Withdrawals: {total_withdrawals}")

    y_position -= 20
    p.drawString(50, y_position, f"Cash Circulation: {cash_circulation}")
    p.drawString(250, y_position, f"Total ROI: {total_roi_percentage}%")
    p.drawString(450, y_position, f"Total Projects: {total_projects}")

    p.showPage()
    p.save()

    # **Send as File Download**
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="transactions.pdf")
