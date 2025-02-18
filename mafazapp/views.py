from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request,'home.html')


def signup(request):
    return render(request,'signup.html')

def login(request):
    return render(request,'login.html')

def userdashboard(request):
    return render(request,'userdashboard.html')

def usertransaction(request):
    return render(request,'usertransaction.html')

def userprojects(request):
    return render(request,'userprojects.html')

def admindashboard(request):
    return render(request,'admindashboard.html')

def adminusers(request):
    return render(request,'adminusers.html')

def admintransaction(request):
    return render(request,'admintransaction.html')

def userledger(request):
    return render(request,'userledger.html')

def adminprojects(request):
    return render(request,'adminprojects.html')





    