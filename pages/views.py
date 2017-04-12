from django.shortcuts import render
from traffic.lib import add_visit

@add_visit
def yourgenome(request):
  return render(request, 'pages/yourgenome.tmpl')
