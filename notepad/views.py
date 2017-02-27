from django.http import HttpResponse

# Create your views here.
def notes(request):
  text = "You've reached the notepad.index view! Path: "+request.path
  return HttpResponse(text, content_type='text/plain; charset=UTF-8')
