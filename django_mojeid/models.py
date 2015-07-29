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

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

try:
    # python3
    from urllib.parse import urlparse, urldefrag
except ImportError:
    # python2
    from urlparse import urlparse, urldefrag


@python_2_unicode_compatible
class Nonce(models.Model):
    user_id = models.IntegerField(null=True)
    server_url = models.CharField(max_length=2047)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=40)

    def __str__(self):
        return "Nonce: %s, %s" % (self.server_url, self.salt)

    @property
    def registration_nonce(self):
        return "%d==%s" % (self.timestamp, self.salt)

    @classmethod
    def get_registration_nonce(cls, registration_nonce):
        # separate using first '=='
        splitted = registration_nonce.split('==', 1)
        if len(splitted) < 2:
            raise cls.DoesNotExist
        timestamp, salt = registration_nonce.split('==')
        return cls.objects.get(timestamp=timestamp, salt=salt)


@python_2_unicode_compatible
class Association(models.Model):
    server_url = models.TextField(max_length=2047)
    handle = models.CharField(max_length=255)
    secret = models.BinaryField(max_length=255)
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField(max_length=64)

    def __str__(self):
        return "Association: %s, %s" % (self.server_url, self.handle)


@python_2_unicode_compatible
class UserOpenID(models.Model):
    user_id = models.IntegerField(primary_key=True)
    claimed_id = models.TextField(max_length=2047, unique=True)

    @property
    def name(self):
        return urlparse(self.claimed_id).netloc

    @property
    def display_id(self):
        return urldefrag(self.claimed_id)[0]

    def __str__(self):
        return self.name
