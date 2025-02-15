from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request,'home.html')


def userdashboard(request):
    return render(request,'userdashboard.html')

def usertransaction(request):
    return render(request,'usertransaction.html')

def userprojects(request):
    return render(request,'userprojects.html')