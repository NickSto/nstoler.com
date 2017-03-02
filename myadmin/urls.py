from django.conf.urls import url
from django.views.generic.base import RedirectView

from . import views

app_name = 'myadmin'
urlpatterns = [
  url(r'^login/submit$', views.login_submit, name='login_submit'),
  url(r'^logout/submit$', views.logout_submit, name='logout_submit'),
  url(r'^hash/submit$', views.hash_submit, name='hash_submit'),
  url(r'^(?P<action>[^/]+)', views.auth_form, name='auth_form'),
]
