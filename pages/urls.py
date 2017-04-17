from django.conf.urls import url

from . import views

app_name = 'pages'
urlpatterns = [
  url(r'^yourgenome$', views.yourgenome, name='yourgenome'),
  url(r'^home$', views.home, name='home'),
]
