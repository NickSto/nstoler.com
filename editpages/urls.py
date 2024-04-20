from django.urls import re_path

from . import views

app_name = 'editpages'

urlpatterns = [
  re_path(r'^view/(?P<page>.+)', views.view, name='view'),
  re_path(r'^additem/(?P<page>.+)', views.additem, name='additem'),
  re_path(r'^edititemform/(?P<page>.+)', views.edititemform, name='edititemform'),
  re_path(r'^edititem/(?P<page>.+)', views.edititem, name='edititem'),
  re_path(r'^deleteitemform/(?P<page>.+)', views.deleteitemform, name='deleteitemform'),
  re_path(r'^deleteitem/(?P<page>.+)', views.deleteitem, name='deleteitem'),
  re_path(r'^moveitem/(?P<page>.+)', views.moveitem, name='moveitem'),
]
