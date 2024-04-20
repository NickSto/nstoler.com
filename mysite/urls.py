from django.urls import include, re_path
from django.views.generic.base import RedirectView
import traffic.views
import editpages.views
import horcrux.views
import worktime.views
import wordle.views

#TODO: Replace `re_path` with `path`
urlpatterns = [
  re_path(r'^misc/', include('misc.urls')),
  re_path(r'^traffic$', traffic.views.monitor, name='traffic_monitor'),
  re_path(r'^traffic/', include('traffic.urls')),
  re_path(r'^editpages/', include('editpages.urls')),
  re_path(r'^page/', include('editpages.urls_view')),
  re_path(r'^$', editpages.views.view, kwargs={'page':'home'}, name='editpages_home'),
  re_path(r'^yourgenome$', editpages.views.view, kwargs={'page':'yourgenome'}, name='editpages_yourgenome'),
  re_path(r'^covid$', editpages.views.view, kwargs={'page':'covid'}, name='editpages_covid'),
  re_path(r'^status$', editpages.views.view, kwargs={'page':'status'}, name='editpages_status'),
  re_path(r'^admin/', include('myadmin.urls')),
  re_path(r'^wikihistory/', include('wikihistory.urls')),
  re_path(r'^ET/', include('ET.urls')),
  re_path(r'^horcrux$', horcrux.views.main, name='horcrux_main'),
  re_path(r'^horcruxes$', RedirectView.as_view(url='/horcrux', permanent=True)),
  re_path(r'^horcrux/', include('horcrux.urls')),
  re_path(r'^wordle$', wordle.views.main, name='wordle_main'),
  re_path(r'^wordle/', include('wordle.urls')),
  re_path(r'^worktime$', worktime.views.main, name='worktime_main'),
  re_path(r'^worktime/', include('worktime.urls')),
  re_path(r'^uptest/', include('uptest.urls')),
  re_path(r'^hax', editpages.views.view, kwargs={'page':'hax'}),
  # If nothing else matches, send it to notepad.
  re_path(r'', include('notepad.urls')),
]
