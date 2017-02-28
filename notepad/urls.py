from django.conf.urls import url

from . import views

app_name = 'notepad'
urlpatterns = [
  url(r'np/random', views.random, name='random'),
  url(r'np/add', views.add, name='add'),
  url(r'np/delete', views.delete, name='delete'),
  url(r'^(?P<page>.+)', views.notes, name='notes'),
]
