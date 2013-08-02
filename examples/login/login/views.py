
from django.shortcuts import render

def login(request):
    """ Display the login page """

    return render(request, 'login.html', {})
