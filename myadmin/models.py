from django.db import models
from utils import ModelMixin

class AdminCookie(ModelMixin, models.Model):
  #TODO: Make connection to Visitor.cookie1 explicit? The problem is one-to-many relationship:
  #      many Visitors can have the same cookie. And if a user visits from a new IP, they appear as
  #      a new Visitor. Would have to update relationships on the fly.
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
