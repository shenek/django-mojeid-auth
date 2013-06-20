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

import re
import urllib

from urlparse import urlsplit, urldefrag

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
try:
    from django.views.decorators.csrf import csrf_exempt
except ImportError:
    from django.contrib.csrf.middleware import csrf_exempt

from openid.consumer.consumer import (
    Consumer, SUCCESS, CANCEL, FAILURE)
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import sreg, ax, pape
from openid.kvform import dictToKV
from openid.yadis.constants import YADIS_CONTENT_TYPE

from django_mojeid.forms import OpenIDLoginForm
from django_mojeid.models import UserOpenID
from django_mojeid.signals import openid_login_complete
from django_mojeid.store import DjangoOpenIDStore
from django_mojeid.exceptions import (
    RequiredAttributeNotReturned,
    DjangoOpenIDException,
    IdentityAlreadyClaimed,
)

from auth import OpenIDBackend
from models import Nonce
from mojeid import Assertion


next_url_re = re.compile('^/[-\w/]+$')

def is_valid_next_url(next):
    # When we allow this:
    #   /openid/?next=/welcome/
    # For security reasons we want to restrict the next= bit to being a local
    # path, not a complete URL.
    return bool(next_url_re.match(next))


def sanitise_redirect_url(redirect_to):
    """Sanitise the redirection URL."""
    # Light security check -- make sure redirect_to isn't garbage.
    is_valid = True
    if not redirect_to or ' ' in redirect_to:
        is_valid = False
    elif '//' in redirect_to:
        # Allow the redirect URL to be external if it's a permitted domain
        allowed_domains = getattr(settings,
            "ALLOWED_EXTERNAL_OPENID_REDIRECT_DOMAINS", [])
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


def render_openid_request(request, openid_request, return_to, trust_root=None):
    """Render an OpenID authentication request."""
    if trust_root is None:
        trust_root = getattr(settings, 'OPENID_TRUST_ROOT',
                             request.build_absolute_uri(reverse(top)))

    if openid_request.shouldSendRedirect():
        redirect_url = openid_request.redirectURL(
            trust_root, return_to)
        return HttpResponseRedirect(redirect_url)
    else:
        form_html = openid_request.htmlMarkup(
            trust_root, return_to, form_tag_attrs={'id': 'openid_message'})
        return HttpResponse(form_html, content_type='text/html;charset=UTF-8')


def default_render_failure(request, message, status=403,
                           template_name='openid/failure.html',
                           exception=None):
    """Render an error page to the user."""
    data = render_to_string(
        template_name, dict(message=message, exception=exception),
        context_instance=RequestContext(request))
    return HttpResponse(data, status=status)


def parse_openid_response(request):
    """Parse an OpenID response from a Django request."""
    # Short cut if there is no request parameters.
    #if len(request.REQUEST) == 0:
    #    return None

    current_url = request.build_absolute_uri()

    consumer = make_consumer(request)
    return consumer.complete(dict(request.REQUEST.items()), current_url)

def login_show(request, login_template='openid/login.html',
               associate_temlate='openid/associate.html',
               form_class=OpenIDLoginForm):

    redirect_to = OpenIDBackend.get_redirect_to(request)

    login_form = form_class(request.POST or None)

    user = OpenIDBackend.get_user_from_request(request)

    template_name = associate_temlate if user else login_template

    return render_to_response(template_name, {
            'form': login_form,
            'action': reverse('openid-init'),
            OpenIDBackend.get_redirect_field_name(): redirect_to
            }, context_instance=RequestContext(request))

def login_begin(request, template_name='openid/login.html',
                login_complete_view='openid-complete',
                form_class=OpenIDLoginForm,
                render_failure=default_render_failure):
    """Begin an OpenID login request, possibly asking for an identity URL."""
    redirect_to = OpenIDBackend.get_redirect_to(request)

    # Get the OpenID URL to try.  First see if we've been configured
    # to use a fixed server URL.
    openid_url = 'https://mojeid.fred.nic.cz/endpoint/'

    login_form = form_class(data=request.POST)
    if login_form.is_valid():
        openid_url = login_form.cleaned_data['openid_identifier']

    error = None
    consumer = make_consumer(request)
    try:
        openid_request = consumer.begin(openid_url)
    except DiscoveryFailure, exc:
        return render_failure(
            request, "OpenID discovery error: %s" % (str(exc),), status=500,
            exception=exc)

    # Request some user details.  If the provider advertises support
    # for attribute exchange, use that.
    attributes = getattr(settings, 'MOJEID_ATTRIBUTES', [])

    fetch_request = ax.FetchRequest()
    for attribute in attributes:
        fetch_request.add(attribute.generate_ax_attrinfo())

    if attributes:
        openid_request.addExtension(fetch_request)
            
    if getattr(settings, 'OPENID_PHYSICAL_MULTIFACTOR_REQUIRED', False):
        preferred_auth = [
            pape.AUTH_MULTI_FACTOR_PHYSICAL,
        ]
        pape_request = pape.Request(preferred_auth_policies=preferred_auth)
        openid_request.addExtension(pape_request)

    # Construct the request completion URL, including the page we
    # should redirect to.
    return_to = request.build_absolute_uri(reverse(login_complete_view))
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

def registration(request, template_name='openid/registration_form.html',
                login_complete_view='openid-complete',
                form_class=OpenIDLoginForm,
                render_failure=default_render_failure):
    """Begin an OpenID login request, possibly asking for an identity URL."""

    registration_url = 'https://mojeid.fred.nic.cz/registration/endpoint/'

    realm = request.build_absolute_uri(reverse(top))

    user = OpenIDBackend.get_user_from_request(request)
    user_id = user.id if user else None

    # Create Nonce
    nonce = Nonce(server_url=realm, user_id=user_id)
    nonce.save()

    fields = []
    attrs = getattr(settings, 'MOJEID_ATTRIBUTES', [])
    # Append attributes to creation request
    if user:
        for attr in attrs:
            form_attr = attr.registration_form_attrs_html(user_id)
            if form_attr:
                fields.append(form_attr)

    return render_to_response(template_name, {
            'fields': fields,
            'action': registration_url,
            'realm': realm,
            'nonce': nonce.registration_nonce,
            }, context_instance=RequestContext(request))

@csrf_exempt
def login_complete(request, render_failure=None):
    redirect_to = OpenIDBackend.get_redirect_to(request)
    render_failure = render_failure or \
                     getattr(settings, 'OPENID_RENDER_FAILURE', None) or \
                     default_render_failure

    openid_response = parse_openid_response(request)
    if not openid_response:
        return render_failure(
            request, 'This is an OpenID relying party endpoint.')

    user_orig = OpenIDBackend.get_user_from_request(request)

    if openid_response.status == SUCCESS:

        try:
            if user_orig:
                #Create association with currently logged in user
                OpenIDBackend.associate_openid_response(user_orig, openid_response)
            else:
                #Create a new user
                user_new = OpenIDBackend.authenticate_using_all_backends(
                    openid_response=openid_response)
                if not user_new:
                    return render_failure(request, 'Unknown user')
                if not OpenIDBackend.is_user_active(user_new):
                    return render_failure(request, 'Disabled account')
                OpenIDBackend.associate_user_with_session(request, user_new)
        except DjangoOpenIDException, e:
            return render_failure(request, e.message, exception=e)

        response = HttpResponseRedirect(sanitise_redirect_url(redirect_to))

        # Notify any listeners that we successfully logged in.
        openid_login_complete.send(sender=UserOpenID, request=request,
            openid_response=openid_response)

        return response

    elif openid_response.status == FAILURE:
        return render_failure(
            request, 'OpenID authentication failed: %s' %
            openid_response.message)
    elif openid_response.status == CANCEL:
        return render_failure(request, 'Authentication cancelled')
    else:
        assert False, (
            "Unknown OpenID response type: %r" % openid_response.status)

@csrf_exempt
def assertion(request):
    """
    MojeID server connects here to propagate a response to the registration
    """
    def _reject(request, error):
        return HttpResponse(dictToKV({'mode': 'reject', 'reason': error}))

    def _accept(request):
        return HttpResponse(dictToKV({'mode': 'accept'}))

    # Accept only post
    if not request.method == 'POST':
        return _reject(request, Assertion.ErrorString.BAD_REQUEST)

    # Accept only valid status
    status = request.POST.get('status')
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
        user_model = OpenIDBackend.get_user_model()
        try:
            user = user_model.objects.get(pk=user_id)
            display_id = urldefrag(claimed_id)[0]
            # Create association
            OpenIDBackend.associate_openid(user, claimed_id, display_id)
        except (user_model.DoesNotExist, IdentityAlreadyClaimed):
            # Don't associte the user when the user doesn't exist or is already claimed
            # And assume that server sent us a valid claimed_id
            pass

    return _accept(request)

def top(request, template_name='openid/top.html'):
    url = request.build_absolute_uri(reverse(xrds))
    title = getattr(settings, 'OPENID_APP_TITLE', 'OpenID Backend')
    return render_to_response(template_name, { 'url': url, 'title': title },
                              context_instance=RequestContext(request)
                             )

def xrds(request, template_name='openid/xrds.xml'):
    return_to_url = request.build_absolute_uri(reverse(login_complete))
    assertion_url = request.build_absolute_uri(reverse(assertion))
    top_url = request.build_absolute_uri(reverse(top))
    return render_to_response(template_name,
                              {'return_to_url': return_to_url,
                               'assertion_url': assertion_url,
                               'top_url': top_url},
                              context_instance=RequestContext(request),
                              content_type=YADIS_CONTENT_TYPE
                             )
