# django-mojeid-auth -  MojeID integration for django.contrib.auth
#
# Copyright (C) 2013-2015 CZ.NIC
# Copyright (C) 2008-2013 Canonical Ltd.
# Copyright (C) 2007 Simon Willison
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import time

try:
    # python3
    from urllib.parse import urlsplit
except ImportError:
    # python2
    from urlparse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from openid.consumer.consumer import SUCCESS, CANCEL, FAILURE
from openid.cryptutil import randomString
from openid.extensions import ax, pape
from openid.fetchers import HTTPFetchingError
from openid.kvform import dictToKV
from openid.message import Message
from openid.store.nonce import NONCE_CHARS
from openid.yadis.constants import YADIS_CONTENT_TYPE

from django_mojeid import errors
from django_mojeid.auth import OpenIDBackend

from django_mojeid.exceptions import (
    DjangoOpenIDException,
    IdentityAlreadyClaimed,
)
from django_mojeid.models import Nonce, UserOpenID
from django_mojeid.mojeid import (
    Assertion,
    get_attributes,
    get_attribute_query,
    get_registration_url,
    create_service,
    MojeIDConsumer
)
from django_mojeid.settings import mojeid_settings
from django_mojeid.signals import (
    user_login_report,
    trigger_error,
    authenticate_user,
    associate_user
)
from django_mojeid.store import DjangoOpenIDStore


SESSION_ATTR_SET_KEY = 'mojeid_attr_set'


def sanitise_redirect_url(redirect_to):
    """Sanitise the redirection URL."""
    # Light security check -- make sure redirect_to isn't garbage.
    is_valid = True
    if not redirect_to or ' ' in redirect_to:
        is_valid = False
    elif '//' in redirect_to:
        # Allow the redirect URL to be external if it's a permitted domain
        allowed_domains = getattr(settings, "ALLOWED_EXTERNAL_OPENID_REDIRECT_DOMAINS", [])
        s, netloc, p, q, f = urlsplit(redirect_to)
        # allow it if netloc is blank or if the domain is allowed
        if netloc:
            # a domain was specified. Is it an allowed domain?
            if netloc.find(":") != -1:
                netloc, _ = netloc.split(":", 1)
            if netloc not in allowed_domains:
                is_valid = False

    # If the return_to URL is not valid, use the default.
    if not is_valid:
        redirect_to = settings.LOGIN_REDIRECT_URL

    return redirect_to


def render_failure(request, error, template_name='openid/failure.html'):
    """Render an error page to the user."""
    # Render the response to trigger_error signal
    resp = trigger_error.send(sender=__name__, error=error, request=request)
    # Return first valid response
    for r in resp:
        if r[1] is not None and isinstance(r[1], HttpResponse):
            return r[1]

    # No response to signal - render default page
    data = render_to_string(template_name, {'message': error.msg},
                            context_instance=RequestContext(request))
    return HttpResponse(data, status=error.http_status)


@require_POST
def login_begin(request, attribute_set='default'):
    """Begin an MojeID login request."""

    if mojeid_settings.MOJEID_SESSION_NEXT_PAGE_ATTR in request.session:
        del request.session[mojeid_settings.MOJEID_SESSION_NEXT_PAGE_ATTR]

    # create consumer, start login process
    consumer = MojeIDConsumer(DjangoOpenIDStore())
    openid_request = consumer.begin(create_service())

    # Request user details.
    attributes = get_attribute_query(attribute_set)
    # save settings set name for response handler
    request.session[SESSION_ATTR_SET_KEY] = attribute_set

    fetch_request = ax.FetchRequest()
    for attribute, required in attributes:
        fetch_request.add(attribute.generate_ax_attrinfo(required))

    if attributes:
        openid_request.addExtension(fetch_request)

    if mojeid_settings.MOJEID_LOGIN_METHOD != 'ANY' or \
            mojeid_settings.MOJEID_MAX_AUTH_AGE is not None:
        # set authentication method to OTP or CERT
        if mojeid_settings.MOJEID_LOGIN_METHOD == "OTP":
            auth_method = [pape.AUTH_MULTI_FACTOR]
        elif mojeid_settings.MOJEID_LOGIN_METHOD == "CERT":
            auth_method = [pape.AUTH_PHISHING_RESISTANT]
        else:
            auth_method = None

        pape_request = pape.Request(
            preferred_auth_policies=auth_method,
            max_auth_age=mojeid_settings.MOJEID_MAX_AUTH_AGE,
        )
        openid_request.addExtension(pape_request)

    # Construct the request completion URL
    return_to = request.build_absolute_uri(reverse(login_complete))

    # get 'next page' and save it to the session
    redirect_to = sanitise_redirect_url(OpenIDBackend.get_redirect_to(request))
    if redirect_to:
        request.session[mojeid_settings.MOJEID_SESSION_NEXT_PAGE_ATTR] = redirect_to

    # Realm should be always something like 'https://example.org/openid/'
    realm = getattr(settings, 'MOJEID_REALM', None)
    if not realm:
        realm = request.build_absolute_uri(reverse(top))

    # we always use POST request
    form_html = openid_request.htmlMarkup(
        realm, return_to, form_tag_attrs={'id': 'openid_message'})
    return HttpResponse(form_html, content_type='text/html; charset=UTF-8')


def registration(request, attribute_set='default',
                 template_name='openid/registration_form.html'):
    """ Try to submit all the registration attributes for mojeID registration"""

    # Realm should be always something like 'https://example.org/openid/'
    realm = getattr(settings, 'MOJEID_REALM',
                    request.build_absolute_uri(reverse(top)))

    user = OpenIDBackend.get_user_from_request(request)
    user_id = user.pk if user else None

    # Create Nonce
    nonce = Nonce(server_url=realm, user_id=user_id,
                  timestamp=time.time(), salt=randomString(35, NONCE_CHARS))
    nonce.save()

    fields = []
    attributes = [x for x in get_attributes(attribute_set) if x.type == 'attribute']
    # Append attributes to creation request if user is valid
    if user:
        for attribute in attributes:
            form_attr = attribute.registration_form_attrs_html(user_id)
            if form_attr:
                fields.append(form_attr)

    # Render the redirection template
    return render_to_response(
        template_name,
        {
            'fields': fields,
            'action': get_registration_url(),
            'realm': realm,
            'nonce': nonce.registration_nonce,
        },
        context_instance=RequestContext(request)
    )


@csrf_exempt
def login_complete(request):
    # Get addres where to redirect after the login
    redirect_to = sanitise_redirect_url(
        request.session.get(mojeid_settings.MOJEID_SESSION_NEXT_PAGE_ATTR))
    attribute_set = request.session.get(SESSION_ATTR_SET_KEY, 'default')

    # clean the session
    if mojeid_settings.MOJEID_SESSION_NEXT_PAGE_ATTR in request.session:
        del request.session[mojeid_settings.MOJEID_SESSION_NEXT_PAGE_ATTR]

    if SESSION_ATTR_SET_KEY in request.session:
        del request.session[SESSION_ATTR_SET_KEY]

    # Get OpenID response and test whether it is valid

    endpoint = create_service()
    message = Message.fromPostArgs(request.REQUEST)
    consumer = MojeIDConsumer(DjangoOpenIDStore())

    try:
        openid_response = consumer.complete(
            message, endpoint, request.build_absolute_uri())
    except HTTPFetchingError:
        # if not using association and can't contact MojeID server
        return render_failure(request, errors.EndpointError())

    # Check whether the user is already logged in
    user_orig = OpenIDBackend.get_user_from_request(request)
    user_model = get_user_model()

    if openid_response.status == SUCCESS:

        try:
            if user_orig:
                # Send a signal to obtain HttpResponse
                resp = associate_user.send(
                    sender=__name__, request=request, openid_response=openid_response,
                    attribute_set=attribute_set, redirect=redirect_to
                )
                resp = [r[1] for r in resp if isinstance(r[1], HttpResponse)]
                if resp:
                    # Return first valid response
                    return resp[0]

                # Create association with currently logged in user
                OpenIDBackend.associate_openid_response(user_orig, openid_response)
            else:
                # Authenticate mojeID user.
                # Send a signal to obtain HttpResponse
                resp = authenticate_user.send(
                    sender=__name__, request=request, openid_response=openid_response,
                    attribute_set=attribute_set, redirect=redirect_to
                )
                resp = [r[1] for r in resp if isinstance(r[1], HttpResponse)]
                if resp:
                    # Return first valid response
                    return resp[0]

                # Perform a default action
                user_new = OpenIDBackend.authenticate_using_all_backends(
                    openid_response=openid_response, attribute_set=attribute_set)
                if not user_new:
                    # Failed to create a user
                    return render_failure(request, errors.UnknownUser())
                if not OpenIDBackend.is_user_active(user_new):
                    # user is deactivated
                    return render_failure(request, errors.DisabledAccount(user_new))
                # Create an association with the new user
                OpenIDBackend.associate_user_with_session(request, user_new)
        except DjangoOpenIDException as e:
            # Something went wrong
            user_id = None
            try:
                # Try to get user id
                user_id = UserOpenID.objects.get(claimed_id=openid_response.identity_url).user_id
            except (UserOpenID.DoesNotExist, user_model.DoesNotExist):
                # Report an error with identity_url
                user_login_report.send(
                    sender=__name__, request=request, username=openid_response.identity_url,
                    method='openid', success=False
                )

            # Report an error with the username
            user_login_report.send(
                sender=__name__, request=request, username=openid_response.identity_url,
                user_id=user_id, method='openid', success=False
            )

            # Render the failure page
            return render_failure(request, errors.AuthenticationFailed(e))

        response = HttpResponseRedirect(redirect_to)

        # Send signal to log the successful login attempt
        user_login_report.send(
            sender=__name__, request=request,
            user_id=user_orig.id if user_orig else user_new.id, method='openid', success=True
        )

        return response

    # Render other failures
    elif openid_response.status == FAILURE:
        user_login_report.send(
            sender=__name__, request=request, username=openid_response.identity_url,
            method='openid', success=False
        )
        return render_failure(request, errors.OpenIDAuthenticationFailed(openid_response))

    elif openid_response.status == CANCEL:
        user_login_report.send(
            sender=__name__, request=request, username=openid_response.identity_url,
            method='openid', success=False
        )
        return render_failure(request, errors.OpenIDAuthenticationCanceled())
    else:
        user_login_report.send(
            sender=__name__, request=request, username=openid_response.identity_url,
            method='openid', success=False
        )
        return render_failure(request, errors.OpenIDUnknownResponseType(openid_response))


@csrf_exempt
def assertion(request):
    """
    mojeID server connects here to propagate a response to the registration
    """
    def _reject(request, error):
        """ Reject response """
        return HttpResponse(dictToKV({'mode': 'reject', 'reason': error}))

    def _accept(request):
        """ Accept response """
        return HttpResponse(dictToKV({'mode': 'accept'}))

    # Accept only post
    if not request.method == 'POST':
        return _reject(request, Assertion.ErrorString.BAD_REQUEST)

    # Accept only valid status
    status = request.POST.get('status', None)
    if not status:
        return _reject(request, Assertion.ErrorString.MISSING_STATUS)
    if status not in Assertion.StatusCodes:
        return _reject(request, Assertion.ErrorString.INVALID_STATUS)

    # TODO check whether this request is from mojeID server and uses https with a proper certificate

    # Test calimed ID
    claimed_id = request.POST.get('claimed_id')
    if not claimed_id:
        return _reject(request, Assertion.ErrorString.MISSING_CLAIMED_ID)

    # The user was registered for mojeID
    if status == Assertion.StatusCodes.REGISTERED:
        registration_nonce = request.POST.get('registration_nonce')
        if registration_nonce is None:
            return _reject(request, Assertion.ErrorString.MISSING_NONCE)

        # check nonce
        try:
            nonce = Nonce.get_registration_nonce(registration_nonce)
        except Nonce.DoesNotExist:
            return _reject(request, Assertion.ErrorString.INVALID_NONCE)

        user_id = nonce.user_id
        nonce.delete()

        # Try to associate the user with mojeID
        if user_id:
            # Fetch the user
            user_model = get_user_model()
            try:
                user = user_model.objects.get(pk=user_id)
                # Create association
                OpenIDBackend.associate_openid(user, claimed_id)
            except (user_model.DoesNotExist, IdentityAlreadyClaimed):
                # Don't associte the user when the user doesn't exist or is already claimed
                # And assume that server sent us a valid claimed_id
                #
                # Note that user might been deleted before this assertion is triggered
                # Or the newly created mojeID account might been already associated
                # with a local account by the client
                #
                # Both of these cases are not considered as errors
                pass

    return _accept(request)


def top(request, template_name='openid/top.html'):
    """ The openid Endpoint
        this page should be only accessible by mojeID server
    """
    url = request.build_absolute_uri(reverse(xrds))
    title = getattr(settings, 'OPENID_APP_TITLE', 'OpenID Backend')
    return render_to_response(
        template_name,
        {'url': url, 'title': title},
        context_instance=RequestContext(request)
    )


def xrds(request, template_name='openid/xrds.xml'):
    """ Render xrds file
        This file should contain assertion and return_to urls.
    """
    return_to_url = request.build_absolute_uri(reverse(login_complete))
    assertion_url = request.build_absolute_uri(reverse(assertion))
    return render_to_response(
        template_name,
        {
            'return_to_url': return_to_url,
            'assertion_url': assertion_url
        },
        context_instance=RequestContext(request),
        content_type=YADIS_CONTENT_TYPE
    )


@require_POST
def disassociate(request):
    """
        Disassociate current user with OpenID
    """

    # Get the User
    user = OpenIDBackend.get_user_from_request(request)
    if not user:
        raise Http404

    # Get OpenID association
    association = OpenIDBackend.get_user_association(user)
    if not association:
        raise Http404

    # Remove the association
    association.delete()

    # Redirect back
    redirect = OpenIDBackend.get_redirect_to(request)
    redirect = redirect if redirect else getattr(settings, 'LOGIN_REDIRECT_URL', '/')
    return HttpResponseRedirect(sanitise_redirect_url(redirect))
