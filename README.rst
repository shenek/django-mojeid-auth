Django OpenID Authentication Support
====================================

This package provides integration between Django's authentication
system and OpenID authentication.  It also includes support for using
a fixed OpenID server endpoint, which can be useful when implementing
single signon systems.


Basic Installation
------------------

1) Install the Jan Rain Python OpenID library.  It can be found at:

        http://openidenabled.com/python-openid/

    It can also be found in most Linux distributions packaged as
    "python-openid".  You will need version 2.2.0 or later.

#) Add 'django_mojeid_auth' to INSTALLED_APPS for your application.
    At a minimum, you'll need the following in there::

        INSTALLED_APPS = (
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django_mojeid_auth',
        )

#) Add 'django_auth_openid.auth.OpenIDBackend' to
    AUTHENTICATION_BACKENDS.  This should be in addition to the
    default ModelBackend::

        AUTHENTICATION_BACKENDS = (
            'django_mojeid_auth.auth.OpenIDBackend',
            'django.contrib.auth.backends.ModelBackend',
        )

#) To create users automatically when a new OpenID is used, add the
    following to the settings:

        OPENID_CREATE_USERS = True

#) Hook up the login URLs to your application's urlconf with
    something like::

        urlpatterns = patterns('',
            ...
            (r'^openid/', include('django_mojeid_auth.urls')),
            ...
        )

#) Configure the LOGIN_URL and LOGIN_REDIRECT_URL appropriately for
    your site::

        LOGIN_URL = '/openid/login/'
        LOGIN_REDIRECT_URL = '/'

    This will allow pages that use the standard @login_required
    decorator to use the OpenID login page.

#) Set the MOJEID_USER_MODEL to specify the user model::

        MOJEID_USER_MODEL = ('auth', 'User', )
    This will force app to use standard django.contrib.auth.User model for authentication

#) Set the MOJEID_ATTRIBUTES to determine which attributes of mojeid should be used::
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

#) Rerun "python manage.py syncdb" to add the UserOpenID table to
    your database.

External redirect domains
-------------------------

By default, redirecting back to an external URL after auth is forbidden. To permit redirection to external URLs on a separate domain, define ALLOWED_EXTERNAL_OPENID_REDIRECT_DOMAINS in your settings.py file as a list of permitted domains::

	ALLOWED_EXTERNAL_OPENID_REDIRECT_DOMAINS = ['example.com', 'example.org']

and redirects to external URLs on those domains will additionally be permitted.

Use as /admin (django.admin.contrib) login
------------------------------------------

If you require openid authentication into the admin application, add the following setting::

        OPENID_USE_AS_ADMIN_LOGIN = True

It is worth noting that a user needs to be be marked as a "staff user" to be able to access the admin interface.  A new openid user will not normally be a "staff user".  
The easiest way to resolve this is to use traditional authentication (OPENID_USE_AS_ADMIN_LOGIN = False) to sign in as your first user with a password and authorise your 
openid user to be staff.

Require Physical Multi-Factor Authentication
--------------------------------------------

If your users should use a physical multi-factor authentication method, such as RSA tokens or YubiKey, add the following setting::

        OPENID_PHYSICAL_MULTIFACTOR_REQUIRED = True
        
If the user's OpenID provider supports the PAPE extension and provides the Physical Multifactor authentication policy, this will
cause the OpenID login to fail if the user does not provide valid physical authentication to the provider.

Override Login Failure Handling
-------------------------------
To override the default OpenID login fail view it is necessary to respond to the signal trigger_error::

        from django_mojeid.signals import trigger_error

        @receiver(trigger_error, dispatch_uid='trigger_error')
        def redirect_to_login(**kwargs):
            request = kwargs['request']
            error = kwargs['error']
            ...
            return HttpResponse(...)

Login Reports
-------------
It is also possible to log the OpenID login attempts thanks to user_login_report signal::

        from django_mojeid.signals import user_login_report

        @receiver(user_login_report, dispatch_uid="login_report")
        def store_report(**kwargs):
            request = kwargs['request']     # request (used to obtain client IP)
            method = kwargs['method']       # Set to 'openid'
            success = kwargs['success']     # True / False
            user_id = kwargs.get('user_id', None) # user_id or username is set
            if not user_id:
                username = kwargs.get('user_name', '')
            ...

Registration
------------
To register an existing user to MojeID a registration form is generated and redirected to mojeid registration page.
Only the attributes marked with use_for_registration=True are passed.

After the registration MojeID server tries to connect to the server and notify it that the registration work well and the existing user can be associated with MojeID account.
This procedure is called Assertion.

Assertion
---------
You need to have a public IP and a valid ssl certificate (not self-signed). You can test your certificat via "openssl s_client ...".
The procedure goes as follows:

1) MojeID server connects to https://example.org/openid and gets addres of xrds.xml
#) MojeID server downloads https://example.org/openid/xrds.xml
#) MojeID server parses the xml file and obtains the assertion url
#) MojeID server opens the assertion url using POST and passes mandatory args
#) Client server verifies the args and associates local user with mojeid account

URL map
-------

**openid/**
    Top OpenID address
**openid/login/**
    Default login page
**openid/initiate/**
    Start the authentication (redirects to OpenID server)
**openid/complete/**
    Finish the authentication (redirects from OpenID server)
**openid/registration/**
    Register new MojeID user (redirects to MojeID server)
**openid/assertion/**
    assertion url (see Assertion)
**openid/xrds.xml**
    xrds.xml (see Assertion)
**openid/disassociate**
    Removes association between current user and OpenID
