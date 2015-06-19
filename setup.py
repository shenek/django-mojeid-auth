#!/usr/bin/env python
# django-mojeid-auth -  MojeID integration for django.contrib.auth
#
# Copyright (C) 2013-2015 CZ.NIC z.s.p.o.
# Copyright (C) 2009-2013 Canonical Ltd.
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
"""mojeID integration for django

A library that can be used to add mojeID support to Django applications.
The library integrates with Django's built in authentication system, so
most applications require minimal changes to support mojeID login. The
library also includes the following features:
  * Attribute Exchange extension.
  * mojeID registration extension.
  * authentication/association handlers.
"""

import sys
from setuptools import setup


# openid dependency
if sys.version_info[0] == 2:
    openidver = ''
else:
    openidver = '3'


description, long_description = __doc__.split('\n\n', 1)
VERSION = '0.2'

setup(
    name='django-mojeid',
    version=VERSION,
    author='CZ.NIC z.s.p.o.',
    author_email='stepan.henek@nic.cz',
    description=description,
    long_description=long_description,
    license='BSD',
    platforms=['any'],
    url='https://gitlab.labs.nic.cz/labs/django-mojeid-auth',
    download_url=('https://gitlab.labs.nic.cz/labs/django-mojeid-auth/repository/archive?ref=%s'
                  % VERSION),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    packages=[
        'django_mojeid',
        'django_mojeid.management',
        'django_mojeid.management.commands',
    ],
    package_data={
        'django_mojeid': [
            'templates/*/*', 'static/*/*', 'locale/*/LC_MESSAGES/*'
        ],
    },
    provides=['django_mojeid'],
    requires=['django (>=1.6)', 'python%s_openid (>=2.2)' % openidver],
    install_requires=['django>=1.6', 'python%s_openid>=2.2' % openidver],
)

