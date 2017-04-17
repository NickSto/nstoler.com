from django.shortcuts import render
from traffic.lib import add_visit

@add_visit
def yourgenome(request):
  return render(request, 'pages/yourgenome.tmpl')


@add_visit
def home(request):
  return render(request, 'pages/home.tmpl')
