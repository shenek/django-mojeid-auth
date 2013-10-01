from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.shortcuts import render, redirect

from django_mojeid.signals import authenticate_user, associate_user


def index(request):
    """ show index page """

    return render(request, 'index.html')


# This overrides a part of the default mojeID login_complete logic
@receiver(associate_user, dispatch_uid="mojeid_associate_user")
@receiver(authenticate_user, dispatch_uid="mojeid_create_user")
def authenticate_user(**kwargs):
    """ Just redirect to index page """
    return redirect(reverse(index))
