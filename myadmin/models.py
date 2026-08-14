from django.db import models
from utils import ModelMixin

class AdminCookie(ModelMixin, models.Model):
  #TODO: Replace with connection to traffic.models.User.
  cookie = models.CharField(max_length=24, null=True, blank=True)

class AdminPassword(ModelMixin, models.Model):
  # Each AdminPassword is associated with one or more AdminDigests.
  # The AdminPassword table exists mainly to group AdminDigests derived from the same password.
  pass

class AdminDigest(ModelMixin, models.Model):
  # Binary values should be stored in hex.
  algorithm = models.CharField(max_length=63)
  hash = models.CharField(max_length=63)
  iterations = models.IntegerField()
  salt = models.CharField(max_length=128)
  digest = models.CharField(max_length=128)
  password = models.ForeignKey(AdminPassword, models.CASCADE)
