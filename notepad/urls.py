from django.urls import re_path

from . import views

app_name = 'notepad'
urlpatterns = [
  re_path(r'^notepad/random$', views.random, name='random'),
  re_path(r'^notepad/topage$', views.topage, name='topage'),
  re_path(r'^notepad/add/(?P<page_name>.+)$', views.add, name='add'),
  re_path(r'^notepad/hideform/(?P<page_name>.+)$', views.hideform, name='hideform'),
  re_path(r'^notepad/hide/(?P<page_name>.+)$', views.hide, name='hide'),
  re_path(r'^notepad/editform/(?P<page_name>.+)$', views.editform, name='editform'),
  re_path(r'^notepad/edit/(?P<page_name>.+)$', views.edit, name='edit'),
  re_path(r'^notepad/moveform/(?P<page_name>.+)$', views.moveform, name='moveform'),
  re_path(r'^notepad/move/(?P<page_name>.+)$', views.move, name='move'),
  re_path(r'^notepad/monitor$', views.monitor, name='monitor'),
  re_path(r'^(?P<page_name>.+)$', views.view, name='view'),
]
