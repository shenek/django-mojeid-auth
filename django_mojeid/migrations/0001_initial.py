# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Nonce'
        db.create_table(u'django_mojeid_nonce', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user_id', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('server_url', self.gf('django.db.models.fields.CharField')(max_length=2047)),
            ('timestamp', self.gf('django.db.models.fields.IntegerField')()),
            ('salt', self.gf('django.db.models.fields.CharField')(max_length=40)),
        ))
        db.send_create_signal(u'django_mojeid', ['Nonce'])

        # Adding model 'Association'
        db.create_table(u'django_mojeid_association', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('server_url', self.gf('django.db.models.fields.TextField')(max_length=2047)),
            ('handle', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('secret', self.gf('django.db.models.fields.TextField')(max_length=255)),
            ('issued', self.gf('django.db.models.fields.IntegerField')()),
            ('lifetime', self.gf('django.db.models.fields.IntegerField')()),
            ('assoc_type', self.gf('django.db.models.fields.TextField')(max_length=64)),
        ))
        db.send_create_signal(u'django_mojeid', ['Association'])

        # Adding model 'UserOpenID'
        db.create_table(u'django_mojeid_useropenid', (
            ('user_id', self.gf('django.db.models.fields.IntegerField')(primary_key=True)),
            ('claimed_id', self.gf('django.db.models.fields.TextField')(unique=True, max_length=2047)),
        ))
        db.send_create_signal(u'django_mojeid', ['UserOpenID'])


    def backwards(self, orm):
        # Deleting model 'Nonce'
        db.delete_table(u'django_mojeid_nonce')

        # Deleting model 'Association'
        db.delete_table(u'django_mojeid_association')

        # Deleting model 'UserOpenID'
        db.delete_table(u'django_mojeid_useropenid')


    models = {
        u'django_mojeid.association': {
            'Meta': {'object_name': 'Association'},
            'assoc_type': ('django.db.models.fields.TextField', [], {'max_length': '64'}),
            'handle': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issued': ('django.db.models.fields.IntegerField', [], {}),
            'lifetime': ('django.db.models.fields.IntegerField', [], {}),
            'secret': ('django.db.models.fields.TextField', [], {'max_length': '255'}),
            'server_url': ('django.db.models.fields.TextField', [], {'max_length': '2047'})
        },
        u'django_mojeid.nonce': {
            'Meta': {'object_name': 'Nonce'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'salt': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'server_url': ('django.db.models.fields.CharField', [], {'max_length': '2047'}),
            'timestamp': ('django.db.models.fields.IntegerField', [], {}),
            'user_id': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        u'django_mojeid.useropenid': {
            'Meta': {'object_name': 'UserOpenID'},
            'claimed_id': ('django.db.models.fields.TextField', [], {'unique': 'True', 'max_length': '2047'}),
            'user_id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['django_mojeid']