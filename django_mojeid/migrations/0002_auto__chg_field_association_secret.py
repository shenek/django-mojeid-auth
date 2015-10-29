# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Remove all associations
        orm.Association.objects.all().delete()

        # Remove and insert the column
        db.delete_column(u'django_mojeid_association', 'secret')
        db.add_column(u'django_mojeid_association', 'secret', self.gf('django.db.models.fields.BinaryField')(max_length=255))

    def backwards(self, orm):

        # Remove all associations
        orm.Association.objects.all().delete()

        # Changing field 'Association.secret'
        db.delete_column(u'django_mojeid_association', 'secret')
        db.add_column(u'django_mojeid_association', 'secret', self.gf('django.db.models.fields.TextField')(max_length=255))

    models = {
        u'django_mojeid.association': {
            'Meta': {'object_name': 'Association'},
            'assoc_type': ('django.db.models.fields.TextField', [], {'max_length': '64'}),
            'handle': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issued': ('django.db.models.fields.IntegerField', [], {}),
            'lifetime': ('django.db.models.fields.IntegerField', [], {}),
            'secret': ('django.db.models.fields.BinaryField', [], {'max_length': '255'}),
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
