from django.conf.urls import url
from django.views.generic.base import RedirectView

from . import views

app_name = 'traffic'
urlpatterns = [
  #TODO: Preserve query string in redirects.
  url(r'^monitor\.cgi', RedirectView.as_view(url='monitor', permanent=True)),
  url(r'^monitor/', RedirectView.as_view(url='../monitor', permanent=True)),
  url(r'^monitor', views.monitor, name='monitor'),
]
