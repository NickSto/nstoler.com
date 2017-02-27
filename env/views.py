from django.shortcuts import render
from django.http import HttpResponse
import os

def index(request):
  text = ''
  for key in sorted(request.META.keys()):
    if key not in os.environ:
      text += '{}:\t{}\n'.format(key, request.META[key])
  return HttpResponse(text, content_type='text/plain; charset=UTF-8')
