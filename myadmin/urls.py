from django.urls import re_path

from . import views

app_name = 'myadmin'
urlpatterns = [
  re_path(r'^(?P<action>[^/]+)/submit$', views.submit, name='submit'),
  re_path(r'^(?P<action>[^/]+)$', views.auth_form, name='auth_form'),
]
