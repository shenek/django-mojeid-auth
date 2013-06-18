#!/usr/bin/python
# -*- coding: utf-8 -*- 

# django-mojeid - MojeID integration for django
#
# Copyright (C) 2013 CZ.NIC
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

from django.core.exceptions import FieldError, ImproperlyConfigured

from openid.extensions import ax

from django_mojeid.exceptions import RequiredAttributeNotReturned

class MojeIDAttribute(object):

    def __init__(self, modelApp, modelClass, modelAttribute, user_id_field_name='user_id', required=True, updatable=False):
        self.modelClass = modelClass
        self.modelApp = modelApp
        self.modelAttribute = modelAttribute
        self.user_id_field_name = user_id_field_name
        self.required = required
        self.updatable = updatable
        self._model = None

    @property
    def model(self):
        if not self._model:
            # Import model during runtime
            from django.db.models.loading import get_model
            # set the model
            self._model = get_model(self.modelApp, self.modelClass)
            if not self._model:
                raise ImproperlyConfigured("Model '%s' from App '%s' does not exist."
                                           % (self.modelClass, self.modelApp))
        return self._model

    def _set(self, record, attribute, value):
        # Simply just set the attribute
        setattr(record, attribute, value)

    def _get_record(self, id):
        packed = {self.user_id_field_name: id}
        return self.model.objects.get(**packed)

    def _get_value(self, response):
        return response.getSingle(self.schema, None)

    def set_model_value(self, id, value):
        record = self._get_record(id)
        if not hasattr(record, self.modelAttribute):
            raise FieldError("Cannot resolve keyword '%s' into field. Choices are: %s"
                             % (self.modelAttribute, ", ".join(record._meta._name_map.keys())))
        self._set(record, self.modelAttribute, value)
        record.save()

    def get_model_value(self, id):
        return getattr(self._get_record(id), self.modelAttribute)

    def generate_ax_attrinfo(self):
        return ax.AttrInfo(self.schema, alias=self.code, required=self.required)

    def get_attribute_and_value(self, response):
        value = self._get_value(response)
        if self.required and value == None:
            raise RequiredAttributeNotReturned(
                "Required Attribute '%s' (%s) was not returned."
                % (self.code, self.text)
            )
        return (self.modelAttribute, value, )

class BirthDate(MojeIDAttribute):
    code = 'birthdate'
    schema = 'http://axschema.org/birthDate'
    text = 'Datum Narození'

class FullName(MojeIDAttribute):
    code = 'fullname'
    schema = 'http://axschema.org/namePerson'
    text = 'Celé jméno'

class FirstName(MojeIDAttribute):
    code = 'firstname'
    schema = 'http://axschema.org/namePerson/first'
    text = 'Jméno'

class LastName(MojeIDAttribute):
    code = 'lastname'
    schema = 'http://axschema.org/namePerson/last'
    text = 'Příjmení'

class NickName(MojeIDAttribute):
    code = 'nick'
    schema = 'http://axschema.org/namePerson/friendly'
    text = 'Přezdívka'

class Company(MojeIDAttribute):
    code = 'company'
    schema = 'http://axschema.org/company/name'
    text = 'Jméno společnosti'

class HomeAddress(MojeIDAttribute):
    code = 'h_address'
    schema = 'http://axschema.org/contact/postalAddress/home'
    text = 'Domácí adresa – Ulice'

class HomeAddress1(MojeIDAttribute):
    code = 'h_address2'
    schema = 'http://axschema.org/contact/postalAddressAdditional/home'
    text = 'Domácí adresa – Ulice2'

class HomeAddress1(MojeIDAttribute):
    code = 'h_address3'
    schema = 'http://specs.nic.cz/attr/addr/main/street3'
    text = 'Domácí adresa – Ulice3'

class HomeCity(MojeIDAttribute):
    code = 'h_city'
    schema = 'http://axschema.org/contact/city/home'
    text = 'Domácí adresa – Město'

class HomeState(MojeIDAttribute):
    code = 'h_state'
    schema = 'http://axschema.org/contact/state/home'
    text = 'Domácí adresa – Stát'

class HomeCountry(MojeIDAttribute):
    code = 'h_country'
    schema = 'http://axschema.org/contact/country/home'
    text = 'Domácí adresa – Země'

class HomePostCode(MojeIDAttribute):
    code = 'h_postcode'
    schema = 'http://axschema.org/contact/postalCode/home'
    text = 'Domácí adresa – PSČ'

class BillingAddress(MojeIDAttribute):
    code = 'b_address'
    schema = 'http://specs.nic.cz/attr/addr/bill/street'
    text = 'Faktur. adresa – Ulice'

class BillingAddress2(MojeIDAttribute):
    code = 'b_address2'
    schema = 'http://specs.nic.cz/attr/addr/bill/street2'
    text = 'Faktur. adresa – Ulice2'

class BillingAddress3(MojeIDAttribute):
    code = 'b_address3'
    schema = 'http://specs.nic.cz/attr/addr/bill/street3'
    text = 'Faktur. adresa – Ulice3'

class BillingCity(MojeIDAttribute):
    code = 'b_city'
    schema = 'http://specs.nic.cz/attr/addr/bill/city'
    text = 'Faktur. adresa – Město'

class BillingState(MojeIDAttribute):
    code = 'b_state'
    schema = 'http://specs.nic.cz/attr/addr/bill/sp'
    text = 'Faktur. adresa – Stát'

class BillingCountry(MojeIDAttribute):
    code = 'b_country'
    schema = 'http://specs.nic.cz/attr/addr/bill/cc'
    text = 'Faktur. adresa – Země'

class BillingPostCode(MojeIDAttribute):
    code = 'b_postcode'
    schema = 'http://specs.nic.cz/attr/addr/bill/pc'
    text = 'Faktur. adresa – PSČ'

class ShippingAddress(MojeIDAttribute):
    code = 's_address'
    schema = 'http://specs.nic.cz/attr/addr/ship/street'
    text = 'Doruč. adresa – Ulice'

class ShippingAddress2(MojeIDAttribute):
    code = 's_address2'
    schema = 'http://specs.nic.cz/attr/addr/ship/street2'
    text = 'Doruč. adresa – Ulice2'

class ShippingAddress3(MojeIDAttribute):
    code = 's_address3'
    schema = 'http://specs.nic.cz/attr/addr/ship/street3'
    text = 'Doruč. adresa – Ulice3'

class ShippingCity(MojeIDAttribute):
    code = 's_city'
    schema = 'http://specs.nic.cz/attr/addr/ship/city'
    text = 'Doruč. adresa – Město'

class ShippingState(MojeIDAttribute):
    code = 's_state'
    schema = 'http://specs.nic.cz/attr/addr/ship/sp'
    text = 'Doruč. adresa – Stát'

class ShippingCountry(MojeIDAttribute):
    code = 's_country'
    schema = 'http://specs.nic.cz/attr/addr/ship/cc'
    text = 'Doruč. adresa – Země'

class ShippingPostCode(MojeIDAttribute):
    code = 's_postcode'
    schema = 'http://specs.nic.cz/attr/addr/ship/pc'
    text = 'Doruč. adresa – PSČ'

class MailingAddress(MojeIDAttribute):
    code = 'm_address'
    schema = 'http://specs.nic.cz/attr/addr/mail/street'
    text = 'Koresp. adresa – Ulice'

class MailingAddress2(MojeIDAttribute):
    code = 'm_address2'
    schema = 'http://specs.nic.cz/attr/addr/mail/street2'
    text = 'Koresp. adresa – Ulice2'

class MailingAddress3(MojeIDAttribute):
    code = 'm_address3'
    schema = 'http://specs.nic.cz/attr/addr/mail/street3'
    text = 'Koresp. adresa – Ulice3'

class MailingCity(MojeIDAttribute):
    code = 'm_city'
    schema = 'http://specs.nic.cz/attr/addr/mail/city'
    text = 'Koresp. adresa – Město'

class MailingState(MojeIDAttribute):
    code = 'm_state'
    schema = 'http://specs.nic.cz/attr/addr/mail/sp'
    text = 'Koresp. adresa – Stát'

class MailingCountry(MojeIDAttribute):
    code = 'm_country'
    schema = 'http://specs.nic.cz/attr/addr/mail/cc'
    text = 'Koresp. adresa – Země'

class MailingPostCode(MojeIDAttribute):
    code = 'm_postcode'
    schema = 'http://specs.nic.cz/attr/addr/mail/pc'
    text = 'Koresp. adresa – PSČ'

class Phone(MojeIDAttribute):
    code = 'phone'
    schema = 'http://axschema.org/contact/phone/default'
    text = 'Telefon – Hlavní'

class PhoneHome(MojeIDAttribute):
    code = 'phone_home'
    schema = 'http://axschema.org/contact/phone/home'
    text = 'Telefon – Domácí'

class PhoneWork(MojeIDAttribute):
    code = 'phone_work'
    schema = 'http://axschema.org/contact/phone/business'
    text = 'Telefon – Pracovní'

class PhoneMobile(MojeIDAttribute):
    code = 'phone_mobile'
    schema = 'http://axschema.org/contact/phone/cell'
    text = 'Telefon – Mobil'

class Fax(MojeIDAttribute):
    code = 'fax'
    schema = 'http://axschema.org/contact/phone/fax'
    text = 'Telefon – Fax'

class Email(MojeIDAttribute):
    code = 'email'
    schema = 'http://axschema.org/contact/email'
    text = 'Email – Hlavní'

class Email2(MojeIDAttribute):
    code = 'email2'
    schema = 'http://specs.nic.cz/attr/email/notify'
    text = 'Email – Notifikační'

class Email3(MojeIDAttribute):
    code = 'email3'
    schema = 'http://specs.nic.cz/attr/email/next'
    text = 'Email – Další'

class Url(MojeIDAttribute):
    code = 'url'
    schema = 'http://axschema.org/contact/web/default'
    text = 'URL – Hlavní'

class Blog(MojeIDAttribute):
    code = 'blog'
    schema = 'http://axschema.org/contact/web/blog'
    text = 'URL – Blog'

class Url2(MojeIDAttribute):
    code = 'url2'
    schema = 'http://specs.nic.cz/attr/url/personal'
    text = 'URL – Osobní'

class Url3(MojeIDAttribute):
    code = 'url3'
    schema = 'http://specs.nic.cz/attr/url/work'
    text = 'URL – Pracovní'

class RSS(MojeIDAttribute):
    code = 'rss'
    schema = 'http://specs.nic.cz/attr/url/rss'
    text = 'URL – RSS'

class Facebook(MojeIDAttribute):
    code = 'fb'
    schema = 'http://specs.nic.cz/attr/url/facebook'
    text = 'URL – Facebook'

class Twitter(MojeIDAttribute):
    code = 'twitter'
    schema = 'http://specs.nic.cz/attr/url/twitter'
    text = 'URL – Twitter'

class LinkedIn(MojeIDAttribute):
    code = 'linkedin'
    schema = 'http://specs.nic.cz/attr/url/linkedin'
    text = 'URL – LinkedIN'

class ICQ(MojeIDAttribute):
    code = 'icq'
    schema = 'http://axschema.org/contact/IM/ICQ'
    text = 'IM – ICQ'

class Jabber(MojeIDAttribute):
    code = 'jabber'
    schema = 'http://axschema.org/contact/IM/Jabber'
    text = 'IM – Jabber'

class Skype(MojeIDAttribute):
    code = 'skype'
    schema = 'http://axschema.org/contact/IM/Skype'
    text = 'IM – Skype'

class GoogleTalk(MojeIDAttribute):
    code = 'gtalk'
    schema = 'http://specs.nic.cz/attr/im/google_talk'
    text = 'IM – Google Talk'

class WindowsLive(MojeIDAttribute):
    code = 'wlive'
    schema = 'http://specs.nic.cz/attr/im/windows_live'
    text = 'IM – Windows Live'

class ICO(MojeIDAttribute):
    code = 'vat_id'
    schema = 'http://specs.nic.cz/attr/contact/ident/vat_id'
    text = 'Identifikátor – ICO'

class DIC(MojeIDAttribute):
    code = 'vat'
    schema = 'http://specs.nic.cz/attr/contact/vat'
    text = 'Identifikátor – DIC'

class IdentityCard(MojeIDAttribute):
    code = 'op'
    schema = 'http://specs.nic.cz/attr/contact/ident/card'
    text = 'Identifikátor – OP'

class Passport(MojeIDAttribute):
    code = 'pas'
    schema = 'http://specs.nic.cz/attr/contact/ident/pass'
    text = 'Identifikátor – PAS'

class MPSV(MojeIDAttribute):
    code = 'mpsv'
    schema = 'http://specs.nic.cz/attr/contact/ident/ssn'
    text = 'Identifikátor – MPSV'

class Student(MojeIDAttribute):
    code = 'student'
    schema = 'http://specs.nic.cz/attr/contact/student'
    text = 'Příznak – Student'

class Valid(MojeIDAttribute):
    code = 'valid'
    schema = 'http://specs.nic.cz/attr/contact/valid'
    text = 'Příznak – Validace'

class Status(MojeIDAttribute):
    code = 'status'
    schema = 'http://specs.nic.cz/attr/contact/status'
    text = 'Stav účtu'

class Adult(MojeIDAttribute):
    code = 'adult'
    schema = 'http://specs.nic.cz/attr/contact/adult'
    text = 'Příznak – Starší 18 let'

class Image(MojeIDAttribute):
    code = 'image'
    schema = 'http://specs.nic.cz/attr/contact/image'
    text = 'Obrázek (base64)'
