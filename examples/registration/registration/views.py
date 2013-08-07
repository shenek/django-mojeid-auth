from django.contrib.auth import logout, login
from django.contrib.auth.models import User
from django.shortcuts import render

from django_mojeid.models import UserOpenID

def index(request):

    # Auto logout
    logout(request)

    # Auto login users
    usecase = int(request.GET.get('usecase', 1))
    usecase = 1 if usecase > 3 else usecase
    user = None
    if usecase == 2:
        user = User.objects.get(username='fvomacka')
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
    if usecase == 3:
        user = User.objects.get(username='jonatan-vomacka')
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

    # Get the claimed ID of the user
    claimed_id = None
    if usecase in [2, 3]:
        try:
            claimed_id = UserOpenID.objects.get(user_id=user.id).claimed_id
        except UserOpenID.DoesNotExist:
            claimed_id = None

    return render(request, 'registration.html', 
                  {'user': user, 'usecase': usecase, 'claimed_id': claimed_id})
