Django mojeID/OpenID Authentication Support
===========================================

This package provides integration between Django's authentication system and OpenID authentication.
It is a fork of https://launchpad.net/django-openid-auth

The main purpose of this fork is to remove launchpad related stuff and add mojeID related stuff.
mojeID is a Czech openid implementation managed by `CZ.NIC z.s.p.o. <http://www.nic.cz/>`_

Basic Installation
------------------

1) Install the Jan Rain Python OpenID library.

   It can be found at: http://openidenabled.com/python-openid/

   It can also be found in most Linux distributions packaged as *python-openid*.
   Version 2.2.0 or later will be needed.

#) Add 'django_mojeid' to INSTALLED_APPS for your application in your *settings.py*.

   At a minimum, you'll need the following in there::

        INSTALLED_APPS = (
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django_mojeid',
        )

#) Add 'django_mojeid.auth.OpenIDBackend' to AUTHENTICATION_BACKENDS in your *settings.py*.

   This should be in addition to the default ModelBackend::

        AUTHENTICATION_BACKENDS = (
            'django_mojeid.auth.OpenIDBackend',
            'django.contrib.auth.backends.ModelBackend',
        )

#) To create users automatically when a new mojeID/OpenID credential is used update your *settings.py*::

        OPENID_CREATE_USERS = True

#) Hook up the login urls to your application's urlconf with::

        urlpatterns = patterns('',
            ...
            (r'^openid/', include('django_mojeid.urls')),
            ...
        )

#) Configure the LOGIN_URL and LOGIN_REDIRECT_URL in your *settings.py* appropriately for your site::

        LOGIN_URL = '/openid/login/'
        LOGIN_REDIRECT_URL = '/'

   This will allow pages that use the standard @login_required
   decorator to be redirected to defined login page.

#) Set the MOJEID_USER_MODEL in your *settings.py* to specify the user model::

        MOJEID_USER_MODEL = ('auth', 'User', )


   This will force app to use standard django.contrib.auth.User model for authentication

#) Set the MOJEID_ATTRIBUTES in your *settings.py* to determine which attributes of mojeid should be used::

        MOJEID_ATTRIBUTES = [
            Email('auth', 'User', 'email', 'pk'),
            FirstName('auth', 'User', 'first_name', 'pk'),
            LastName('auth', 'User', 'last_name', 'pk', updatable=True, required=False),
            NickName('auth', 'User', 'username', 'pk', use_for_registration=False),
            Phone('example_app', 'UserExtraAttributes', 'phone', 'user_id'),
            ]

   - First four parameters are mandatory. First parameter is an app name.
   - Second is a model name. Third models attribute.
   - Fourth is an attribute which holds the user id.
   - required(=True) - fail authentication when this attr is not obtained from mojeid
   - updatable(=False) - update the attributes of the model after login
   - use_for_registration(=True) - prefill mojeid registration form with this attribute

#) Sync your database to add all necessary tables::

    python manage.py syncdb

#) Set the proper mojeID server.

   By default all mojeID related actions are performed against the testing server https://mojeid.fred.nic.cz
   To use the actual mojeID server you need to set two variables in your *settings.py*::

        MOJEID_ENDPOINT_URL = 'https://mojeid.cz/endpoint/'
        MOJEID_REGISTRATION_URL = 'https://mojeid.cz/registration/endpoint/'

Realm
-----

    A "realm" is a pattern that represents the part of URL-space for which an OpenID Authentication request is valid.

see http://openid.net/specs/openid-authentication-2_0-12.html#realms

Realm is also used to identify the web from which the client was redirected to the mojeID registration page.
Note that only the sites with properly set realm can participate in `Incentive programme for web service providers <http://www.mojeid.cz/page/877/motivacni-program-pro-poskytovatele-sluzeb/>`_.

To set a realm you can simply place following line into *settings.py*::

    MOJEID_REALM = 'https://myweb.com/'

Note that it is necessary to include following meta tag to your realm page::

    <meta http-equiv="x-xrds-location" content="https://myweb.com/openid/xrds.xml" />

The OpenID/mojeID servers will be looking for the xrds.xml file so you need set this tag.

mojeID Attributes
-----------------
Where are defined
Types
How are they used
etc.

External redirect domains
-------------------------

By default, redirecting back to an external URL after authentication is forbidden.
To permit redirection to external URLs on a separate domain, define ALLOWED_EXTERNAL_OPENID_REDIRECT_DOMAINS in your settings.py file as a list of permitted domains::

    ALLOWED_EXTERNAL_OPENID_REDIRECT_DOMAINS = ['example.com', 'example.org']

Redirects to external URLs on those domains will additionally be permitted.

Use as /admin (django.admin.contrib) login
------------------------------------------

If you require openid authentication into the admin application, add the following setting::

    OPENID_USE_AS_ADMIN_LOGIN = True

It is worth noting that a user needs to be marked as a "staff user" to be able to access the admin interface.
A new openid user will not normally be a "staff user".
The easiest way to resolve this is to use traditional authentication (OPENID_USE_AS_ADMIN_LOGIN = False) to sign in as your first user with a password and authorize your openid user to be staff.

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

This can be triggered e.g. when a user doesn't provide the required attributes from OpenID/mojeID server.
By default this view is quite ugly and when you want to integrate error messages into your web app you are encouraged to respond to this signal.

Custom handlers
---------------
The attribute which is obtained from mojeID server is usually used to update a part of an existing model.
If we don't want to update a model we can create a *CustomHandler* structure instead of *MojeIDAttribute*.
This handler is linked to a function which we choose.

In *settings.py*::

    MOJEID_ATTRIBUTES = [
        ...
        mojeid.CustomHandler(mojeid.FullName, 'full_name_handler', required=True),
        ]

Handler code::

    from django_mojeid.attribute_handlers import register_handler

    @register_handler('full_name_handler')
    def print_fullname_to_console(user, full_name):
        print '>>>', full_name, '<<< for user ', user


Note that you need the handler code to be executed.
A simple way to do so is to put the code inside some python file e.g. *handlers.py* and import it from *__init__.py* (*import handlers*).

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

Override Authentication or Association
---------------------------------------
The basic logic of the authentication or association can be overwritten.
This could be useful when we want just to obtain some attributes from mojeID without authenticating the user.
*(For example we could obtain an up-to-date home address to ship our goods)*

To override the authentication action you simply::

    from django_mojeid.signals import authenticate_user

    @receiver(authenticate_user, dispatch_uid="mojeid_create_user")
    def authenticate(**kwargs):
        request = kwargs['request']
        openid_response = kwargs['openid_response']
        redirect_to = kwargs['redirect']
        ...
        openid_attributes = OpenIDBackend.get_model_changes(openid_response)
        ...
        return redirect(url)

You can override the association action in a similar way::

    from django_mojeid.signals import associate_user

    @receiver(associate_user, dispatch_uid="mojeid_associate_user")
    def associate_user(**kwargs):
        request = kwargs['request']
        openid_response = kwargs['openid_response']
        redirect_to = kwargs['redirect']
        claimed_id = openid_response.endpoint.claimed_id
        ...
        openid_attributes = OpenIDBackend.get_model_changes(openid_response)
        ...
        return redirect(redirect_to)

Both of these functions should return a *HttpResponse* object.
Otherwise the default action is trigger after the execution.

Note that no login reports are generated when you override these actions.
But you can still send the report in these functions.

To see both functions in action see *examples/login* and *examples/association*

Registration
------------
To register an existing user to mojeID a registration form is generated and redirected to mojeid registration page.
Only the attributes marked with use_for_registration=True are passed.

After the registration mojeID server tries to connect to the server and notify it that the registration work well and the existing user can be associated with mojeID account.
This procedure is called Assertion.

Assertion
---------
You need to have a public IP and a valid ssl certificate (not self-signed). You can test your certificate via "openssl s_client ...".
The procedure goes as follows:

1) mojeID server connects to https://example.org/openid and gets addres of xrds.xml
#) mojeID server downloads https://example.org/openid/xrds.xml
#) mojeID server parses the xml file and obtains the assertion url
#) mojeID server opens the assertion url using POST and passes mandatory args
#) Client server verifies the args and associates local user with mojeID account

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
    Register new mojeID user (redirects to mojeID server)
**openid/assertion/**
    assertion url (see Assertion)
**openid/xrds.xml**
    xrds.xml (see Assertion)
**openid/disassociate/**
    Removes association between current user and OpenID

Examples
--------
TBD in /examples/


Troubleshooting
---------------
TBD

Localhost related stuff

SSL certificate verificiation via openssl
