from django import forms
from .models import CustomUser,InvestmentProject,Transaction,UserProjectAssignment
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from django.contrib.auth import get_user_model


class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'address', 'country', 'password']


    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  
        user.status = 'PENDING'  # Ensure status is always set to PENDING on sign-up
        if commit:
            user.save()
        return user

    


from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ForgotPasswordForm(forms.Form):
    email_or_username = forms.CharField(max_length=150, required=True)

    def clean_email_or_username(self):
        data = self.cleaned_data["email_or_username"]
        if not User.objects.filter(email=data).exists() and not User.objects.filter(username=data).exists():
            raise forms.ValidationError("No user found with this email or username.")
        return data





# user update profile


# update profile form
from django import forms
from django.contrib.auth import get_user_model


class UserProfileUpdateForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'input-field'}),
        help_text="Leave blank if you don't want to change the password.",
    )

    country = CountryField().formfield(
        widget=CountrySelectWidget(attrs={'class': 'form-control'})
    )

    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'address', 'country', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('password')

        if new_password:
            user.set_password(new_password)  # Hash and set the password

        if commit:
            user.save()

        return user


# project form
class InvestmentProjectForm(forms.ModelForm):
    class Meta:
        model = InvestmentProject
        fields = ['project_name', 'total_investment', 'min_roi', 'max_roi', 'project_description', 'images']
        widgets = {
            'project_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class TransactionForm(forms.ModelForm):
    User = get_user_model() 
    
    class Meta:
        model = Transaction
        fields = ['user', 'amount', 'project', 'transaction_type', 'narration', 'receipt']


class UserTransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'project', 'transaction_type', 'narration', 'receipt']
    
    def __init__(self, *args, **kwargs):
        super(UserTransactionForm, self).__init__(*args, **kwargs)
        self.fields['amount'].widget.attrs.update({'placeholder': 'Enter amount'})
        self.fields['narration'].widget.attrs.update({'placeholder': 'Enter narration'})



class UserProjectAssignmentForm(forms.ModelForm):
    class Meta:
        model = UserProjectAssignment
        fields = ['user', 'project', 'roi']

    def __init__(self, *args, **kwargs):
        super(UserProjectAssignmentForm, self).__init__(*args, **kwargs)
        self.fields['roi'].widget.attrs.update({'placeholder': 'Enter ROI (optional)'})
        

 
from .models import UserDocument

class UserDocumentForm(forms.ModelForm):
    class Meta:
        model = UserDocument
        fields = ['document_type', 'file']
