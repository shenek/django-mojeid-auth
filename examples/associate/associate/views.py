from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.shortcuts import render, redirect
from django.http import QueryDict

from django_mojeid.auth import OpenIDBackend
from django_mojeid.models import UserOpenID
from django_mojeid.signals import associate_user

def associate(request):
    """ Display the associate page """

    # Auto login user
    username = request.GET.get('username', 'jvomacka')
    user = User.objects.get(username=username)
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)

    # Other user
    other_user = 'fvomacka' if username == 'jvomacka' else 'jvomacka'

    return render(request, 'associate.html', 
                  {'why_my_id_url': 'https://www.nic.cz/', 'other_user': other_user})

def display_associate(request):
    """ Display user who is going to be associated """
    return render(request, 'associate_confirm.html', dict(request.GET))

def display_disassociate(request):
    """ user and claimed_id is already associated and needs to be disassociated first """
    params = dict(request.GET)
    if 'user_associated' in request.GET:
        user_associated = User.objects.get(username=request.GET['user_associated'])
        params['user_associated'] = user_associated 
    return render(request, 'disassociate.html', params)


@receiver(associate_user, dispatch_uid="mojeid_associate_user")
def associate_user(**kwargs):
    """ Display associate forms prefilled with data from mojeID """
    request = kwargs['request']
    openid_response = kwargs['openid_response']
    redirect_to = kwargs['redirect']
    claimed_id = openid_response.endpoint.claimed_id
    user_associated = None
    claimed_associated = None

    # Check whether the claimed_id is already associated
    if UserOpenID.objects.filter(claimed_id__exact=claimed_id).exists():
        path = reverse(display_disassociate)
        user_associated = User.objects.get(pk=UserOpenID.objects.get(
            claimed_id__exact=claimed_id).user_id)
    else:
        if UserOpenID.objects.filter(user_id=request.user.id).exists():
            path = reverse(display_disassociate)
            claimed_associated = UserOpenID.objects.get(user_id=request.user.id).claimed_id
        else:
            path = reverse(display_associate)
            # Associate the user
            #OpenIDBackend.associate_openid_response(request.user, openid_response)

    # Update all updatable attributes
    #attrs = OpenIDBackend.update_user_from_openid(user_id, openid_response)
    # Or Just display the updatable attributes to be updated
    attrs = OpenIDBackend.get_model_changes(openid_response, only_updatable=True)

    # set the params for redirect
    qd = QueryDict('').copy()
    params = attrs.get(User, {})
    params['next'] = redirect_to
    params['claimed_id'] = claimed_id
    if user_associated:
        params['user_associated'] = user_associated
    if claimed_associated:
        params['claimed_associated'] = claimed_associated
    if 'user_id_field_name' in params:
        del params['user_id_field_name']
    qd.update(params)

    url = "%s?%s" % (path, qd.urlencode())
    return redirect(url)
