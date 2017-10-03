from django.conf.urls import url

from . import views

app_name = 'traffic'
urlpatterns = [
  # Redirect to special view in order to preserve query string.
  url(r'^monitor\.cgi$', views.monitor_redirect),
  url(r'^monitor/$', views.monitor_redirect),
  url(r'^monitor$', views.monitor_redirect),
  url(r'^markallbots$', views.mark_all_robots, name='markallbots'),
  url(r'^markbot$', views.mark_robot, name='markbot'),
  url(r'^$', views.monitor, name='monitor'),
]
