from django.conf.urls import url

from . import views

app_name = 'editpages'

urlpatterns = [
  url(r'^view/(?P<page>.+)', views.view, name='view'),
  url(r'^additem/(?P<page>.+)', views.additem, name='additem'),
  url(r'^edititemform/(?P<page>.+)', views.edititemform, name='edititemform'),
  url(r'^edititem/(?P<page>.+)', views.edititem, name='edititem'),
  url(r'^deleteitemform/(?P<page>.+)', views.deleteitemform, name='deleteitemform'),
  url(r'^deleteitem/(?P<page>.+)', views.deleteitem, name='deleteitem'),
  url(r'^moveitem/(?P<page>.+)', views.moveitem, name='moveitem'),
]
