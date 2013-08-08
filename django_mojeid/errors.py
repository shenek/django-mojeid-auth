class GeneralError(object):
    http_status = 500
    name = 'general'
    text = 'General OpenID error.'

    def __repr__(self):
        return self.text

class DiscoveryError(GeneralError):
    http_status = 404
    name = 'discovery'
    text = "OpenID discovery error"

    def __init__(self, exception):
        self.exception = exception

    def __repr__(self):
        return "%s: %s" % (self.text, str(self.exception.message))

class EndpointError(GeneralError):
    name = 'endpoint'
    text = 'This is an OpenID relying party endpoint.'

class UnknownUser(GeneralError):
    http_status = 404
    name = 'unknown_user'
    text = 'Unknown User'

class DisabledAccount(GeneralError):
    http_status = 403
    name = 'disabled_account'
    text = 'Disabled Account'

    def __init__(self, user):
        self.user = user

    def __repr__(self):
        return "%s for User with id=%d" % (self.text, self.user.id)

class AuthenticationFailed(GeneralError):
    http_status = 403
    name = 'auth_failed'
    text = 'Authentication Failed'

    def __init__(self, exception):
        self.exception = exception

    def __repr__(self):
        return "%s: %s" % (self.text, str(self.exception.message))

class OpenIDAuthenticationFailed(GeneralError):
    http_status = 403
    name = 'openid_auth_failed'
    text = 'OpenID authentication failed'

    def __init__(self, openid_response):
        self.openid_response = openid_response

    def __repr__(self):
        return "%s: %s" % (self.text, str(self.openid_response.message))


class OpenIDAuthenticationCanceled(GeneralError):
    http_status = 403
    name = 'openid_auth_cancelled'
    text = 'OpenID Authentication Cancelled'

class OpenIDUnknownResponseType(GeneralError):
    name = 'openid_unknown'
    text = 'OpenID Unknown Response Type'
    def __init__(self, openid_response):
        self.openid_response = openid_response

    def __repr__(self):
        return "%s: %s" % (self.text, str(self.openid_response.status))
