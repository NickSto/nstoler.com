from django.shortcuts import render


def yourgenome(request):
  return render(request, 'pages/yourgenome.tmpl')


def home(request):
  return render(request, 'pages/home.tmpl')
