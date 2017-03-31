from django.conf.urls import url

from . import views

app_name = 'notepad'
urlpatterns = [
  url(r'^notepad/random$', views.random, name='random'),
  url(r'^notepad/add/(?P<page_name>.+)$', views.add, name='add'),
  url(r'^notepad/delete/(?P<page_name>.+)$', views.delete, name='delete'),
  url(r'^notepad/monitor$', views.monitor, name='monitor'),
  url(r'^(?P<page_name>.+)$', views.view, name='view'),
]
