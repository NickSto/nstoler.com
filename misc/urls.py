from django.urls import re_path

from . import views

app_name = 'misc'
urlpatterns = [
  re_path(r'^env$', views.env, name='env'),
  re_path(r'^userinfo$', views.userinfo, name='userinfo'),
  re_path(r'^setcookie$', views.setcookie, name='setcookie'),
  re_path(r'^export$', views.export, name='export'),
  re_path(r'^captcha/(?P<name>.+)$', views.captcha, name='captcha'),
  re_path(r'^captchasubmit/(?P<name>.+)$', views.captchasubmit, name='captchasubmit'),
  re_path(r'^journalurl/(?P<proxy>[^/]+)/(?P<url>.+)$', views.journalurl, name='journalurl')
]
