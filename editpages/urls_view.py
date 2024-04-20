from django.urls import re_path

from . import views

app_name = 'page'

urlpatterns = [
  re_path(r'^(?P<page>.+)', views.view, name='view'),
]
