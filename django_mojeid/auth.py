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

"""OpenID authentication"""

from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from openid.consumer.consumer import SUCCESS
from openid.extensions import ax

from django_mojeid.exceptions import (
    IdentityAlreadyClaimed,
    DuplicateUserViolation,
)
from django_mojeid.mojeid import get_attributes
from django_mojeid.attribute_handlers import call_handler


class OpenIDBackend:
    """A backend that authenticates the user based on an OpenID response."""

    supports_object_permissions = False
    supports_anonymous_user = True

    @classmethod
    def get_user_from_request(cls, request):
        """This method can be overwritten to implement custom user/session mechanizms
        currently it uses standard django.contrib.auth"""
        if not hasattr(request, 'user') or not hasattr(request.user, 'is_authenticated'):
            return None
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

    @classmethod
    def is_user_associated_with_openid(cls, user):
        if not user:
            return False
        from django_mojeid.models import UserOpenID
        return UserOpenID.objects.filter(user_id=user.pk).exists()

    @classmethod
    def get_user_association(cls, user):
        from django_mojeid.models import UserOpenID
        if not user:
            return None
        try:
            association = UserOpenID.objects.get(user_id=user.pk)
        except UserOpenID.DoesNotExist:
            association = None

        return association

    @classmethod
    def get_redirect_to(cls, request):
        """This method can be overwritten to implement custom user/session mechanizms
        currently it uses standard django.contrib.auth"""
        return request.REQUEST.get(cls.get_redirect_field_name(), '')

    @classmethod
    def get_redirect_field_name(cls):
        """This method can be overwritten to implement custom user/session mechanizms
        currently it uses standard django.contrib.auth"""
        from django.contrib.auth import REDIRECT_FIELD_NAME
        return REDIRECT_FIELD_NAME

    @staticmethod
    def authenticate_using_all_backends(**credentials):
        """This method can be overwritten to implement custom user/session mechanizms
        currently it uses standard django.contrib.auth"""
        from django.contrib.auth import authenticate
        return authenticate(**credentials)

    @classmethod
    def associate_user_with_session(cls, request, user):
        """This method can be overwritten to implement custom user/session mechanizms
        currently it uses standard django.contrib.auth"""
        from django.contrib.auth import login as auth_login

        # skip when the user is not authenticated (=AnonymousUser)
        if not user or not user.is_authenticated():
            return

        # Set backend if it is not set
        if not hasattr(user, 'backend'):
            setattr(user, 'backend', 'django_mojeid.auth.OpenIDBackend')

        auth_login(request, user)

    def authenticate(self, **kwargs):
        """Authenticate the user based on an OpenID response."""
        # Require that the OpenID response be passed in as a keyword
        # argument, to make sure we don't match the username/password
        # calling conventions of authenticate.

        from django_mojeid.models import UserOpenID

        openid_response = kwargs.get('openid_response')
        if openid_response is None:
            return None

        attribute_set = kwargs.get('attribute_set', 'default')

        if openid_response.status != SUCCESS:
            return None

        user = None
        new_user = False
        try:
            user_openid = UserOpenID.objects.get(
                claimed_id__exact=openid_response.identity_url)
        except UserOpenID.DoesNotExist:
            if getattr(settings, 'OPENID_CREATE_USERS', False):
                user = self.create_user_from_openid(openid_response, attribute_set)
                new_user = True
        else:
            user_model = get_user_model()
            try:
                user = user_model.objects.get(pk=user_openid.user_id)
            except user_model.DoesNotExist:
                user = None

        if user is None:
            return None

        if not new_user:
            self.update_user_from_openid(user.pk, openid_response, attribute_set)

        # Run custom Attribute handler
        OpenIDBackend.run_handlers(openid_response, user, attribute_set)

        return user

    @staticmethod
    def get_model_changes(openid_response, only_updatable=False,
                          attribute_set='default'):

        attributes = [x for x in get_attributes(attribute_set)
                      if x.type in ['attribute', 'internal']]

        fetch_response = ax.FetchResponse.fromSuccessResponse(openid_response)

        res = {}

        # filter remove non-updatable attributes
        if only_updatable:
            attributes = [x for x in attributes if x.updatable]

        for attribute in attributes:
            if attribute.model not in res:
                res[attribute.model] = {'user_id_field_name': attribute.user_id_field_name}
            val = attribute.get_value(fetch_response, attribute.required,
                                      openid_response=openid_response)

            if val is not None:
                res[attribute.model][attribute.modelAttribute] = val

        return res

    @staticmethod
    def run_handlers(openid_response, user, attribute_set='default'):
        handlers = [x for x in get_attributes(attribute_set) if x.type == 'handler']

        if not handlers:
            return

        fetch_response = ax.FetchResponse.fromSuccessResponse(openid_response)

        for handler in handlers:
            val = handler.attribute.get_value(fetch_response, handler.required, openid_response)
            call_handler(handler.name, user, val)

    def create_user_from_openid(self, openid_response, attribute_set='default'):
        changes = OpenIDBackend.get_model_changes(openid_response, attribute_set=attribute_set)

        user_model = get_user_model()

        # Id will be generated no need to set this field
        del changes[user_model]['user_id_field_name']

        # Create the main user structure
        user = user_model(**changes[user_model])
        try:
            user.validate_unique()
        except ValidationError as e:
            raise DuplicateUserViolation(", ".join(e.messages))
        user.save()

        # User created remove it from the dict
        del changes[user_model]

        # Create other structures
        for model, kwargs in changes.items():
            foreign_key_name = kwargs['user_id_field_name']
            del kwargs['user_id_field_name']
            kwargs[foreign_key_name] = user.pk
            m = model(**kwargs)
            m.save()

        OpenIDBackend.associate_openid_response(user, openid_response)

        return user

    @classmethod
    def update_user_from_openid(cls, user_id, openid_response, attribute_set='default'):
        changes = OpenIDBackend.get_model_changes(openid_response, only_updatable=True,
                                                  attribute_set=attribute_set)

        for model, kwargs in changes.items():
            foreign_key_name = kwargs['user_id_field_name']
            del kwargs['user_id_field_name']
            model.objects.filter(**{foreign_key_name: user_id}).update(**kwargs)

        return changes

    @staticmethod
    def associate_openid_response(user, openid_response):
        """Associate an OpenID request with a user account."""
        # Check to see if this OpenID has already been claimed.
        return OpenIDBackend.associate_openid(user, openid_response.identity_url)

    @staticmethod
    def associate_openid(user, claimed_id):
        """Associate an OpenID with a user account."""

        from django_mojeid.models import UserOpenID

        # Check to see if this OpenID has already been claimed.
        try:
            user_openid = UserOpenID.objects.get(
                claimed_id__exact=claimed_id)
        except UserOpenID.DoesNotExist:
            user_openid = UserOpenID(
                user_id=user.pk,
                claimed_id=claimed_id)
            user_openid.save()
        else:
            if user_openid.user_id != user.pk:
                raise IdentityAlreadyClaimed(
                    _("The identity %s has already been claimed")
                    % claimed_id)

        return user_openid

    @classmethod
    def get_user(cls, user_id):
        try:
            user_model = get_user_model()
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
