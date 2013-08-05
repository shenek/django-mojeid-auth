from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.shortcuts import render, redirect
from django.http import QueryDict

from django_mojeid.signals import authenticate_user
from django_mojeid.auth import OpenIDBackend
from django_mojeid.models import UserOpenID

def login(request):
    """ Display the login page """

    # Auto logout
    logout(request)

    return render(request, 'login.html', {})

def new_user(request):
    """ Display new user form """
    return render(request, 'new_user.html', dict(request.GET))

@login_required
def display_user(request):
    """ Display existing user """
    return render(request, 'existing_user.html', dict(request.GET))

# This overrides a part of the default MojeID login_complete logic
@receiver(authenticate_user, dispatch_uid="mojeid_create_user")
def authenticate_user(**kwargs):
    """ Display create user form prefilled with data from MojeID """
    request = kwargs['request']
    openid_response = kwargs['openid_response']
    redirect_to = kwargs['redirect']

    # Get the user
    try:
        # Authenticate user
        user_openid = UserOpenID.objects.get(
            claimed_id__exact=openid_response.identity_url)
        user = OpenIDBackend.get_user(user_openid.user_id)
        OpenIDBackend.associate_user_with_session(request, user)

        # Update all updatable attributes
        #attrs = OpenIDBackend.update_user_from_openid(user_id, openid_response)
        # Or Just display the updatable attributes to be updated
        attrs = OpenIDBackend.get_model_changes(openid_response, only_updatable=True)

        # Set url path
        path = reverse(display_user)

    except UserOpenID.DoesNotExist:
        # Create user

        # Get attributes for the new User model
        attrs = OpenIDBackend.get_model_changes(openid_response)

        # Set url path
        path = reverse(new_user)

    # set the params for redirect
    qd = QueryDict('').copy()
    params = attrs.get(User, {})
    params['next'] = redirect_to
    if 'user_id_field_name' in params:
        del params['user_id_field_name']
    qd.update(params)

    url = "%s?%s" % (path, qd.urlencode())
    return redirect(url)
