from django.conf.urls import url

from . import views

app_name = 'notepad'
urlpatterns = [
  url(r'^notepad/random$', views.random, name='random'),
  url(r'^notepad/topage$', views.topage, name='topage'),
  url(r'^notepad/add/(?P<page_name>.+)$', views.add, name='add'),
  url(r'^notepad/hideform/(?P<page_name>.+)$', views.hideform, name='hideform'),
  url(r'^notepad/hide/(?P<page_name>.+)$', views.hide, name='hide'),
  url(r'^notepad/editform/(?P<page_name>.+)$', views.editform, name='editform'),
  url(r'^notepad/edit/(?P<page_name>.+)$', views.edit, name='edit'),
  url(r'^notepad/moveform/(?P<page_name>.+)$', views.moveform, name='moveform'),
  url(r'^notepad/move/(?P<page_name>.+)$', views.move, name='move'),
  url(r'^notepad/monitor$', views.monitor, name='monitor'),
  url(r'^(?P<page_name>.+)$', views.view, name='view'),
]
