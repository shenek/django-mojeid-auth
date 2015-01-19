from __future__ import unicode_literals

import sys

from django.utils.translation import ugettext_lazy as _


if sys.version_info.major != 2:
    unicode = str


class GeneralError(object):
    http_status = 500
    name = 'general'
    text = _('General OpenID error.')

    @property
    def msg(self):
        return self.text


class DiscoveryError(GeneralError):
    http_status = 404
    name = 'discovery'
    text = _("OpenID discovery error")

    def __init__(self, exception):
        self.exception = exception

    @property
    def msg(self):
        return '%s: %s' % (self.text, unicode(self.exception))


class EndpointError(GeneralError):
    name = 'endpoint'
    text = _('This is an OpenID relying party endpoint.')


class UnknownUser(GeneralError):
    http_status = 404
    name = 'unknown_user'
    text = _('Unknown User')


class DisabledAccount(GeneralError):
    http_status = 403
    name = 'disabled_account'
    text = _('Disabled Account')

    def __init__(self, user):
        self.user = user

    @property
    def msg(self):
        return '%s for User with id=%d' % (self.text, self.user.pk)


class AuthenticationFailed(GeneralError):
    http_status = 403
    name = 'auth_failed'
    text = _('Authentication Failed')

    def __init__(self, exception):
        self.exception = exception

    @property
    def msg(self):

        return '%s: %s' % (self.text, unicode(self.exception))


class OpenIDAuthenticationFailed(GeneralError):
    http_status = 403
    name = 'openid_auth_failed'
    text = _('OpenID authentication failed')

    def __init__(self, openid_response):
        self.openid_response = openid_response

    @property
    def msg(self):
        return '%s: %s' % (self.text, unicode(self.openid_response.message))


class OpenIDAuthenticationCanceled(GeneralError):
    http_status = 403
    name = 'openid_auth_cancelled'
    text = _('OpenID Authentication Cancelled')


class OpenIDUnknownResponseType(GeneralError):
    name = 'openid_unknown'
    text = _('OpenID Unknown Response Type')

    def __init__(self, openid_response):
        self.openid_response = openid_response

    @property
    def msg(self):
        return '%s: %d' % (self.text, self.openid_response.status)
