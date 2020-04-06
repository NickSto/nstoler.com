from django.conf.urls import url

from . import views

app_name = 'page'

urlpatterns = [
  url(r'^(?P<page>.+)', views.view, name='view'),
]
