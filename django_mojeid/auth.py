# django-openid-auth -  OpenID integration for django.contrib.auth
#
# Copyright (C) 2013 CZ.NIC
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

"""Glue between OpenID and django.contrib.auth."""

__metaclass__ = type

import re

from django.conf import settings
from django.db.models.loading import get_model
from openid.consumer.consumer import SUCCESS
from openid.extensions import ax, pape

from django_mojeid.models import UserOpenID
from django_mojeid.exceptions import (
    IdentityAlreadyClaimed,
    MissingPhysicalMultiFactor,
)

class OpenIDBackend:
    """A django.contrib.auth backend that authenticates the user based on
    an OpenID response."""

    supports_object_permissions = False
    supports_anonymous_user = True

    @classmethod
    def get_user(cls, user_id):
        try:
            user_model = OpenIDBackend.get_user_model()
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None

    @classmethod
    def get_user_from_request(cls, request):
        """This method can be overwritten to implement custom user/session mechanizms
        currently it uses standard django.contrib.auth"""
        return request.user if request.user.is_authenticated() else None

    @classmethod
    def is_user_active(cls, user):
        """This method can be overwritten to implement custom user/session mechanizms
        currently it uses standard django.contrib.auth"""
        return user.is_active if user else False

    @classmethod
    def is_user_authenticated(cls, user):
        """This method can be overwritten to implement custom user/session mechanizms
        currently it uses standard django.contrib.auth"""
        return user.is_authenticated() if user else False

    def authenticate(self, **kwargs):
        """Authenticate the user based on an OpenID response."""
        # Require that the OpenID response be passed in as a keyword
        # argument, to make sure we don't match the username/password
        # calling conventions of authenticate.

        openid_response = kwargs.get('openid_response')
        if openid_response is None:
            return None

        if openid_response.status != SUCCESS:
            return None

        user = None
        new_user = False
        try:
            user_openid = UserOpenID.objects.get(
                claimed_id__exact=openid_response.identity_url)
        except UserOpenID.DoesNotExist:
            if getattr(settings, 'OPENID_CREATE_USERS', False):
                user = self.create_user_from_openid(openid_response)
                new_user = True
        else:
            user_model = OpenIDBackend.get_user_model()
            try:
                user = user_model.objects.get(pk=user_openid.user_id)
            except user_model.DoesNotExist:
                user = None

        if user is None:
            return None

        if not new_user:
            self.update_user_from_openid(user.id, openid_response)

        if getattr(settings, 'OPENID_PHYSICAL_MULTIFACTOR_REQUIRED', False):
            pape_response = pape.Response.fromSuccessResponse(openid_response)
            if pape_response is None or \
               pape.AUTH_MULTI_FACTOR_PHYSICAL not in pape_response.auth_policies:
                raise MissingPhysicalMultiFactor()

        return user

    def _get_model_changes(self, openid_response, only_updatable=False):

        attributes = getattr(settings, 'MOJEID_ATTRIBUTES', [])

        fetch_response = ax.FetchResponse.fromSuccessResponse(openid_response)

        res = {}

        # filter remove non-updatable attributes
        if only_updatable:
            attributes = [x for x in attributes if x.updatable]

        for attribute in attributes:
            if not attribute.model in res.keys():
                res[attribute.model] = {'user_id_field_name': attribute.user_id_field_name}
            key, val = attribute.get_attribute_and_value(fetch_response)

            if val != None:
                res[attribute.model][key] = val

        return res

    def create_user_from_openid(self, openid_response):
        changes = self._get_model_changes(openid_response)

        user_model = OpenIDBackend.get_user_model()

        # Id will be generated no need to set this field
        del changes[user_model]['user_id_field_name']

        # Create the main user structure
        user = user_model(**changes[user_model])
        user.save()

        # User created remove it from the dict
        del changes[user_model]

        # Create other structures
        for model, kwargs in changes.iteritems():
            foreign_key_name = kwargs['user_id_field_name']
            del kwargs['user_id_field_name']
            kwargs[foreign_key_name] = user.id
            m = model(**kwargs)
            m.save()

        OpenIDBackend.associate_openid_response(user, openid_response)

        return user

    def update_user_from_openid(self, user_id, openid_response):
        changes = self._get_model_changes(openid_response, only_updatable=True)

        user_model = OpenIDBackend.get_user_model()

        for model, kwargs in changes.iteritems():
            foreign_key_name = kwargs['user_id_field_name']
            del kwargs['user_id_field_name']
            model.objects.filter(**{foreign_key_name: user_id}).update(**kwargs)

    @staticmethod
    def associate_openid_response(user, openid_response):
        """Associate an OpenID request with a user account."""
        # Check to see if this OpenID has already been claimed.
        return OpenIDBackend.associate_openid(
            user, openid_response.identity_url,
            openid_response.endpoint.getDisplayIdentifier())

    @staticmethod
    def associate_openid(user, claimed_id, display_id):
        """Associate an OpenID with a user account."""
        # Check to see if this OpenID has already been claimed.
        try:
            user_openid = UserOpenID.objects.get(
                claimed_id__exact=claimed_id)
        except UserOpenID.DoesNotExist:
            user_openid = UserOpenID(
                user_id=user.id,
                claimed_id=claimed_id,
                display_id=display_id)
            user_openid.save()
        else:
            if user_openid.user_id != user.id:
                raise IdentityAlreadyClaimed(
                    "The identity %s has already been claimed"
                    % claimed_id)

        return user_openid

    @staticmethod
    def get_user_model():
        app_name, model_name = getattr(settings, 'MOJEID_USER_MODEL')
        return get_model(app_name, model_name)
