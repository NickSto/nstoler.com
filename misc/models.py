from django.db import models
from utils import ModelMixin

# Minimally structured temporary storage bin.
class TempData(ModelMixin, models.Model):
  # A number you can use to identify the data later E.g. pass it to a background task so it can
  # create a TempData when it's done, then find it via the identifier in the main thread.
  identifier = models.IntegerField(null=True, blank=True)
  type = models.CharField(max_length=127)
  int = models.IntegerField(null=True, blank=True)
  float = models.FloatField(null=True, blank=True)
  data = models.TextField()
