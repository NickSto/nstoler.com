from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import RedirectView
import traffic.views
import editpages.views
import horcrux.views
import worktime.views

urlpatterns = [
  # url(r'^admin/', include(admin.site.urls)),
  url(r'^misc/', include('misc.urls')),
  url(r'^traffic$', traffic.views.monitor, name='traffic_monitor'),
  url(r'^traffic/', include('traffic.urls')),
  url(r'^editpages/', include('editpages.urls')),
  url(r'^$', editpages.views.view, kwargs={'page':'home'}, name='editpages_home'),
  url(r'^yourgenome$', editpages.views.view, kwargs={'page':'yourgenome'}, name='editpages_yourgenome'),
  url(r'^status$', editpages.views.view, kwargs={'page':'status'}, name='editpages_status'),
  url(r'^admin/', include('myadmin.urls')),
  url(r'^wikihistory/', include('wikihistory.urls')),
  url(r'^ET/', include('ET.urls')),
  url(r'^horcrux$', horcrux.views.main, name='horcrux_main'),
  url(r'^horcruxes$', RedirectView.as_view(url='/horcrux', permanent=True)),
  url(r'^horcrux/', include('horcrux.urls')),
  url(r'^worktime$', worktime.views.main, name='worktime_main'),
  url(r'^worktime/', include('worktime.urls')),
  url(r'^uptest/', include('uptest.urls')),
  url(r'^hax', editpages.views.view, kwargs={'page':'hax'}),
  # If nothing else matches, send it to notepad.
  url(r'', include('notepad.urls')),
]
