from django.shortcuts import render

# Create your views here.
def index(request):
  context = {'text':'Hello, world.'}
  return render(request, 'testapp/index.html', context)
