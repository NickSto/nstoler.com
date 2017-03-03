from django.conf.urls import url

from . import views

app_name = 'notepad'
urlpatterns = [
  url(r'np/random', views.random, name='random'),
  url(r'np/add/(?P<page>.+)', views.add, name='add'),
  url(r'np/delete/(?P<page>.+)', views.delete, name='delete'),
  url(r'^(?P<page>.+)', views.notes, name='notes'),
]
