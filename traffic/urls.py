from django.urls import re_path

from . import views

app_name = 'traffic'
urlpatterns = [
  # Redirect to special view in order to preserve query string.
  re_path(r'^monitor\.cgi$', views.monitor_redirect),
  re_path(r'^monitor$', views.monitor_redirect),
  re_path(r'^ip/(?P<ip>.+)$', views.view_ip, name='view_ip'),
  re_path(r'^ip$', views.view_ip),
  re_path(r'^markallbots$', views.mark_all_robots, name='markallbots'),
  re_path(r'^markbot$', views.mark_robot, name='markbot'),
  re_path(r'^$', views.monitor, name='monitor'),
]
