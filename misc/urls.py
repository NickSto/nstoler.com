from django.conf.urls import url
from django.views.generic.base import RedirectView

from . import views

app_name = 'misc'
urlpatterns = [
  url(r'^env$', views.env, name='env'),
  url(r'^userinfo$', views.userinfo, name='userinfo'),
  url(r'^setcookie$', views.setcookie, name='setcookie'),
  url(r'^dataurl$', views.dataurl, name='dataurl'),
  url(r'^sessionrecover$', views.sessionrecover, name='sessionrecover'),
  url(r'^export$', views.export, name='export'),
  url(r'^captcha/(?P<name>.+)$', views.captcha, name='captcha'),
  url(r'^captchasubmit/(?P<name>.+)$', views.captchasubmit, name='captchasubmit'),
]
