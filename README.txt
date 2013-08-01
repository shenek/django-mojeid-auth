= Django OpenID Authentication Support =

This package provides integration between Django's authentication
system and OpenID authentication.  It also includes support for using
a fixed OpenID server endpoint, which can be useful when implementing
single signon systems.


== Basic Installation ==

 1. Install the Jan Rain Python OpenID library.  It can be found at:

        http://openidenabled.com/python-openid/

    It can also be found in most Linux distributions packaged as
    "python-openid".  You will need version 2.2.0 or later.

 2. Add 'django_mojeid_auth' to INSTALLED_APPS for your application.
    At a minimum, you'll need the following in there:

        INSTALLED_APPS = (
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django_mojeid_auth',
        )

 3. Add 'django_auth_openid.auth.OpenIDBackend' to
    AUTHENTICATION_BACKENDS.  This should be in addition to the
    default ModelBackend:

        AUTHENTICATION_BACKENDS = (
            'django_mojeid_auth.auth.OpenIDBackend',
            'django.contrib.auth.backends.ModelBackend',
        )

 4. To create users automatically when a new OpenID is used, add the
    following to the settings:

        OPENID_CREATE_USERS = True

 5. Hook up the login URLs to your application's urlconf with
    something like:

        urlpatterns = patterns('',
            ...
            (r'^openid/', include('django_mojeid_auth.urls')),
            ...
        )

 6. Configure the LOGIN_URL and LOGIN_REDIRECT_URL appropriately for
    your site:

        LOGIN_URL = '/openid/login/'
        LOGIN_REDIRECT_URL = '/'

    This will allow pages that use the standard @login_required
    decorator to use the OpenID login page.

 7. Set the MOJEID_USER_MODEL to specify the user model:

        MOJEID_USER_MODEL = ('auth', 'User', )
    This will force app to use standard django.contrib.auth.User model for authentication

 8. Set the MOJEID_ATTRIBUTES to determine which attributes of mojeid should be used:
    MOJEID_ATTRIBUTES = [
        Email('auth', 'User', 'email', 'pk'),
        FirstName('auth', 'User', 'first_name', 'pk'),
        LastName('auth', 'User', 'last_name', 'pk', updatable=True, required=False),
        NickName('auth', 'User', 'username', 'pk', use_for_registration=False),
        Phone('example_app', 'UserExtraAttributes', 'phone', 'user_id'),
    ]
    First four parameters are mandatory. First parameter is an app name.
    Second is a model name. Third models attribute.
    Fourth is an attribute which holds the user id.
    required(=True) - fail authentication when this attr is not obtained from mojeid
    updatable(=False) - update the attributes of the model after login
    use_for_registration - prefill mojeid registration form with this attribute

 9. Rerun "python manage.py syncdb" to add the UserOpenID table to
    your database.

== External redirect domains ==

By default, redirecting back to an external URL after auth is forbidden. To permit redirection to external URLs on a separate domain, define ALLOWED_EXTERNAL_OPENID_REDIRECT_DOMAINS in your settings.py file as a list of permitted domains:

	ALLOWED_EXTERNAL_OPENID_REDIRECT_DOMAINS = ['example.com', 'example.org']

and redirects to external URLs on those domains will additionally be permitted.

== Use as /admin (django.admin.contrib) login ==

If you require openid authentication into the admin application, add the following setting:

        OPENID_USE_AS_ADMIN_LOGIN = True

It is worth noting that a user needs to be be marked as a "staff user" to be able to access the admin interface.  A new openid user will not normally be a "staff user".  
The easiest way to resolve this is to use traditional authentication (OPENID_USE_AS_ADMIN_LOGIN = False) to sign in as your first user with a password and authorise your 
openid user to be staff.

== Require Physical Multi-Factor Authentication ==

If your users should use a physical multi-factor authentication method, such as RSA tokens or YubiKey, add the following setting:

        OPENID_PHYSICAL_MULTIFACTOR_REQUIRED = True
        
If the user's OpenID provider supports the PAPE extension and provides the Physical Multifactor authentication policy, this will
cause the OpenID login to fail if the user does not provide valid physical authentication to the provider.

== Override Login Failure Handling ==

== Updating Attributes ==
when
how

== Registration ==

== Assertion ==

== Error handling ==
