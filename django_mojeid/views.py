# django-openid-auth -  OpenID integration for django.contrib.auth
#
# Copyright (C) 2013 CZ.NIC
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

import urllib

from urlparse import urlsplit

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import get_language, activate as activate_lang

from openid.consumer.consumer import (
    Consumer, SUCCESS, CANCEL, FAILURE)
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import ax, pape
from openid.kvform import dictToKV
from openid.yadis.constants import YADIS_CONTENT_TYPE

from django_mojeid.forms import OpenIDLoginForm
from django_mojeid.models import UserOpenID
from django_mojeid.mojeid import (
    MOJEID_REGISTRATION_URL,
    MOJEID_ENDPOINT_URL,
    get_attributes,
    get_attribute_query,
)
from django_mojeid.signals import (
    user_login_report,
    trigger_error,
    authenticate_user,
    associate_user
)
from django_mojeid.store import DjangoOpenIDStore
from django_mojeid.exceptions import (
    DjangoOpenIDException,
    IdentityAlreadyClaimed,
)
from django.contrib.auth import get_user_model

import errors

from django_mojeid.auth import OpenIDBackend
from django_mojeid.models import Nonce
from django_mojeid.mojeid import Assertion
from django_mojeid.settings import mojeid_settings

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


def make_consumer(request):
    """Create an OpenID Consumer object for the given Django request."""
    # Give the OpenID library its own space in the session object.
    session = request.session.setdefault('OPENID', {})
    store = DjangoOpenIDStore()
    return Consumer(session, store)


def render_openid_request(request, openid_request, return_to):
    """ Render an OpenID authentication request.
        This request will automatically redirect client to OpenID server.
    """

    # Realm should be always something like 'https://example.org/openid/'
    realm = getattr(settings, 'MOJEID_REALM',
                    request.build_absolute_uri(reverse(top)))

    # Directly redirect to the OpenID server
    if openid_request.shouldSendRedirect():
        redirect_url = openid_request.redirectURL(realm, return_to)
        return HttpResponseRedirect(redirect_url)

    # Render a form wich will redirect the client
    else:
        form_html = openid_request.htmlMarkup(realm, return_to,
                                              form_tag_attrs={'id': 'openid_message'})
        return HttpResponse(form_html, content_type='text/html;charset=UTF-8')


def render_failure(request, error, template_name='openid/failure.html'):
    """Render an error page to the user."""
    # Render the response to trigger_error signal
    resp = trigger_error.send(sender=__name__, error=error, request=request)
    resp = filter(lambda r: not r[1] is None and isinstance(r[1], HttpResponse), resp)
    if resp:
        # Return first valid response
        return resp[0][1]

    # No response to signal - render default page
    data = render_to_string(template_name, {'message': error.msg},
                            context_instance=RequestContext(request))
    return HttpResponse(data, status=error.http_status)


def parse_openid_response(request):
    """Parse an OpenID response from a Django request."""

    current_url = request.build_absolute_uri()

    consumer = make_consumer(request)
    attribute_set = consumer.session.get('attribute_set', 'default')
    lang = consumer.session.get('stored_lang', 'en')
    return attribute_set, lang, consumer.complete(dict(request.REQUEST.items()),
                                                  current_url)


def login_show(request, login_template='openid/login.html',
               associate_template='openid/associate.html',
               form_class=OpenIDLoginForm):
    """
    Render a template to show the login/associate form form.
    """

    redirect_to = OpenIDBackend.get_redirect_to(request)

    login_form = form_class(request.POST or None)

    user = OpenIDBackend.get_user_from_request(request)

    template_name = associate_template if user else login_template

    return render_to_response(
        template_name,
        {
            'form': login_form,
            'action': reverse('openid-init'),
            OpenIDBackend.get_redirect_field_name(): redirect_to
        },
        context_instance=RequestContext(request)
    )


@require_POST
def login_begin(request, attribute_set='default', form_class=OpenIDLoginForm):
    """Begin an MojeID login request."""
    redirect_to = OpenIDBackend.get_redirect_to(request)

    openid_url = getattr(settings, 'MOJEID_ENDPOINT_URL', MOJEID_ENDPOINT_URL)

    login_form = form_class(data=request.POST)
    if login_form.is_valid():
        openid_url = login_form.cleaned_data['openid_identifier']

    consumer = make_consumer(request)

    # Set response handler (define the settings set)
    consumer.session['attribute_set'] = attribute_set

    # Set the language
    consumer.session['stored_lang'] = request.POST.get('lang', get_language())
    request.session.save()

    try:
        openid_request = consumer.begin(openid_url)
    except DiscoveryFailure, exc:
        return render_failure(request, errors.DiscoveryError(exc))

    # Request user details.
    attributes = get_attribute_query(attribute_set)

    fetch_request = ax.FetchRequest()
    for attribute, required in attributes:
        fetch_request.add(attribute.generate_ax_attrinfo(required))

    if attributes:
        openid_request.addExtension(fetch_request)
    
    if mojeid_settings.MOJEID_LOGIN_METHOD != 'ANY':
        # set authentication method to OTP or CERT
        if mojeid_settings.MOJEID_LOGIN_METHOD == "OTP":
            auth_method = pape.AUTH_MULTI_FACTOR
        else: # mojeid_settings.MOJEID_LOGIN_METHOD == "CERT":
            auth_method = pape.AUTH_PHISHING_RESISTANT
        
        pape_request = pape.Request(preferred_auth_policies=[auth_method])
        openid_request.addExtension(pape_request)
    
    # Construct the request completion URL, including the page we
    # should redirect to.
    return_to = request.build_absolute_uri(reverse(login_complete))
    if redirect_to:
        if '?' in return_to:
            return_to += '&'
        else:
            return_to += '?'
        # Django gives us Unicode, which is great.  We must encode URI.
        # urllib enforces str. We can't trust anything about the default
        # encoding inside  str(foo) , so we must explicitly make foo a str.
        return_to += urllib.urlencode(
            {OpenIDBackend.get_redirect_field_name(): redirect_to.encode("UTF-8")})

    return render_openid_request(request, openid_request, return_to)


def registration(request, attribute_set='default',
                 template_name='openid/registration_form.html',
                 form_class=OpenIDLoginForm):
    """ Try to submit all the registration attributes for mojeID registration"""

    registration_url = getattr(settings, 'MOJEID_REGISTRATION_URL',
                               MOJEID_REGISTRATION_URL)

    # Realm should be always something like 'https://example.org/openid/'
    realm = getattr(settings, 'MOJEID_REALM',
                    request.build_absolute_uri(reverse(top)))

    user = OpenIDBackend.get_user_from_request(request)
    user_id = user.pk if user else None

    # Create Nonce
    nonce = Nonce(server_url=realm, user_id=user_id)
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
            'action': registration_url,
            'realm': realm,
            'nonce': nonce.registration_nonce,
        },
        context_instance=RequestContext(request)
    )


@csrf_exempt
def login_complete(request):
    # Get addres where to redirect after the login
    redirect_to = sanitise_redirect_url(OpenIDBackend.get_redirect_to(request))

    # Get OpenID response and test whether it is valid
    attribute_set, lang, openid_response = parse_openid_response(request)

    # Set language
    activate_lang(lang)

    if not openid_response:
        return render_failure(request, errors.EndpointError())

    # Check whether the user is already logged in
    user_orig = OpenIDBackend.get_user_from_request(request)
    user_model = get_user_model()

    if openid_response.status == SUCCESS:

        try:
            if user_orig:
                # Send a signal to obtain HttpResponse
                resp = associate_user.send(sender=__name__, request=request,
                                           openid_response=openid_response,
                                           attribute_set=attribute_set,
                                           redirect=redirect_to)
                resp = [r[1] for r in resp if isinstance(r[1], HttpResponse)]
                if resp:
                    # Return first valid response
                    return resp[0]

                # Create association with currently logged in user
                OpenIDBackend.associate_openid_response(user_orig, openid_response)
            else:
                # Authenticate mojeID user.
                # Send a signal to obtain HttpResponse
                resp = authenticate_user.send(sender=__name__, request=request,
                                              openid_response=openid_response,
                                              attribute_set=attribute_set,
                                              redirect=redirect_to)
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
        except DjangoOpenIDException, e:
            # Something went wrong
            user_id = None
            try:
                # Try to get user id
                user_id = UserOpenID.objects.get(claimed_id=openid_response.identity_url).user_id
            except UserOpenID.DoesNotExist, user_model.DoesNotExist:
                # Report an error with identity_url
                user_login_report.send(sender=__name__,
                                       request=request,
                                       username=openid_response.identity_url,
                                       method='openid',
                                       success=False)

            # Report an error with the username
            user_login_report.send(sender=__name__,
                                   request=request,
                                   username=openid_response.identity_url,
                                   user_id=user_id,
                                   method='openid',
                                   success=False)

            # Render the failure page
            return render_failure(request, errors.AuthenticationFailed(e))

        response = HttpResponseRedirect(redirect_to)

        # Send signal to log the successful login attempt
        user_login_report.send(sender=__name__,
                               request=request,
                               user_id=user_orig.id if user_orig else user_new.id,
                               method='openid',
                               success=True)

        return response

    # Render other failures
    elif openid_response.status == FAILURE:
        user_login_report.send(sender=__name__,
                               request=request,
                               username=openid_response.identity_url,
                               method='openid',
                               success=False)
        return render_failure(request, errors.OpenIDAuthenticationFailed(openid_response))

    elif openid_response.status == CANCEL:
        user_login_report.send(sender=__name__,
                               request=request,
                               username=openid_response.identity_url,
                               method='openid',
                               success=False)
        return render_failure(request, errors.OpenIDAuthenticationCanceled())
    else:
        user_login_report.send(sender=__name__,
                               request=request,
                               username=openid_response.identity_url,
                               method='openid',
                               success=False)
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
    if not status in Assertion.StatusCodes:
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
