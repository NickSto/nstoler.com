from django.conf.urls import url

from . import views

app_name = 'editpages'

urlpatterns = [
  url(r'^view/(?P<page>.+)', views.view, name='view'),
  url(r'^edittext/(?P<page>.+)', views.edittext, name='edittext'),
  url(r'^edititem/(?P<page>.+)', views.edititem, name='edititem'),
  url(r'^modifylist/(?P<page>.+)', views.modifylist, name='modifylist'),
  url(r'^modifylistitem/(?P<page>.+)', views.modifylistitem, name='modifylistitem'),
  url(r'^addlist/(?P<page>.+)', views.addlist, name='addlist'),
  url(r'^addlistitem/(?P<page>.+)', views.addlistitem, name='addlistitem'),
  url(r'^$', views.view, kwargs={'page':'home'}, name='view_home'),
]
