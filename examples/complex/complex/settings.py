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

# Django settings for example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'sqlite.db'
    }
}

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Prague'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '34958734985734985734985798437'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

# from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS
# TEMPLATE_CONTEXT_PROCESSORS += ('django.core.context_processors.request', )

ROOT_URLCONF = 'complex.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

STATIC_URL = '/static/'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django_mojeid',
    'example_app',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'openid': {
            'handlers': ['console'],
            'filters': ['require_debug_false'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

AUTHENTICATION_BACKENDS = (
    'django_mojeid.auth.OpenIDBackend',
    'django.contrib.auth.backends.ModelBackend',
)

# Should users be created when new OpenIDs are used to log in?
OPENID_CREATE_USERS = True

# Tell django.contrib.auth to use the OpenID signin URLs.
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# Should django_auth_openid be used to sign into the admin interface?
OPENID_USE_AS_ADMIN_LOGIN = False

# For production set the urls to actual mojeid server
# MOJEID_ENDPOINT_URL = 'https://mojeid.cz/endpoint/'
# MOJEID_REGISTRATION_URL = 'https://mojeid.cz/registration/endpoint/'

# Set a custom REALM (by deafult https://myweb.com/openid/)
# Note that you need to include meta header which points to xrds.xml in MOJEID_REALM page
# (e.g. <meta http-equiv="x-xrds-location" content="https://myweb.com/openid/xrds.xml" />)
# MOJEID_REALM = 'https://myweb.com/'

# Setting of mojeID attributes
from django_mojeid import mojeid
MOJEID_ATTRIBUTES_SETS = {
    'default': [
        mojeid.Email('auth', 'User', 'email', 'pk'),
        #mojeid.FullName(User, 'username', 'id'),
        mojeid.FirstName('auth', 'User', 'first_name', 'pk'),
        mojeid.LastName('auth', 'User', 'last_name', 'pk', updatable=True, required=False),
        mojeid.NickName('auth', 'User', 'username', 'pk', use_for_registration=False),
        mojeid.Student('example_app', 'UserExtraAttributes', 'student', 'user_id', updatable=True),
        mojeid.Phone('example_app', 'UserExtraAttributes', 'phone', 'user_id'),
        mojeid.CustomHandler(mojeid.FullName, 'full_name_handler', required=True),
    ],
    'other': [
        mojeid.Email('auth', 'User', 'email', 'pk'),
        mojeid.NickName('auth', 'User', 'username', 'pk'),
        mojeid.CustomHandler(mojeid.Adult, 'adult_handler', required=True),
        mojeid.CustomHandler(mojeid.Validated, 'valid_handler', required=True),
    ]
}
