from django.conf.urls import url
from django.views.generic.base import RedirectView

from . import views

app_name = 'myadmin'
urlpatterns = [
  url(r'^(?P<action>[^/]+)/submit$', views.submit, name='submit'),
  url(r'^(?P<action>[^/]+)$', views.auth_form, name='auth_form'),
]
