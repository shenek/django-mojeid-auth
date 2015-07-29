# django-openid-auth -  OpenID integration for django.contrib.auth
#
# Copyright (C) 2007 Simon Willison
# Copyright (C) 2008-2013 Canonical Ltd.
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

from django.conf import settings
from django.conf.urls import patterns, url

from django_mojeid import views

urlpatterns = patterns(
    '',
    url(r'^$', views.top, name='openid-top'),
    url(r'^xrds.xml$', views.xrds, name='openid-xrds'),
    url(r'^disassociate/$', views.disassociate, name='openid-disassociate'),
    url(r'^initiate/$', views.login_begin, name='openid-init'),
    url(r'^initiate/(?P<attribute_set>\w*)$', views.login_begin, name='openid-init'),
    url(r'^complete/$', views.login_complete, name='openid-complete'),
)

if getattr(settings, 'USE_MOJEID_REGISTRATION_URLS', True):
    urlpatterns += patterns(
        '',
        url(r'^registration/$', views.registration, name='openid-registration'),
        url(r'^registration/(?P<attribute_set>\w*)$', views.registration,
            name='openid-registration'),
        url(r'^assertion/$', views.assertion, name='openid-assertion'),
    )
