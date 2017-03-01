from django.conf.urls import url

from . import views

app_name = 'traffic'
urlpatterns = [
  # #TODO: Redirect 301 from monitor.cgi to monitor.
  url(r'^monitor(?:\.cgi|/)?', views.monitor, name='monitor'),
]
