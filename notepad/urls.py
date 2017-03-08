from django.conf.urls import url

from . import views

app_name = 'notepad'
urlpatterns = [
  url(r'^notepad/random$', views.random, name='random'),
  url(r'^notepad/add/(?P<page>.+)$', views.add, name='add'),
  url(r'^notepad/delete/(?P<page>.+)$', views.delete, name='delete'),
  url(r'^notepad/monitor$', views.monitor, name='monitor'),
  url(r'^(?P<page>.+)$', views.view, name='view'),
]
