from django.db import models

from django.contrib.auth.models import User

class UserExtraAttributes(models.Model):
    user = models.ForeignKey(User)
    adult = models.NullBooleanField(null=True)
    student = models.NullBooleanField(null=True)
    phone = models.CharField(max_length=15, null=True)
