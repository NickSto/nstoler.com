Port from 1.0
--------

Database export:
https://nstoler.com/traffic/export-visits.cgi
https://nstoler.com/np/export.cgi
- `$ pg_dump django`

Small utilities?
http://nstoler.com/misc/userinfo.cgi
http://nstoler.com/misc/dataurl.html
http://nstoler.com/misc/urlconv.html

Notepad
-------

Fix spacing between lines:
* on copy/paste, empty lines appear between every real one.
    - I think it's actually because each line is a `<p>` now.
* Maybe try just pasting the literal text, without `<p>`'s
    - Rely on white-space: pre-wrap to break lines.

Allow non-admins to see /notepad/monitor.
- Only show pages they've edited.

Traffic
-------
Allow non-admins to see `/traffic/monitor`.
- only show their visits.

Allow admin to filter for a specific user/visitor's visits.

`watch_nginx.py`: Log every non-Django visit, but add flags for things like `handler` and `via`.

Optional filters:
- Try to filter out bots.
- Filter out "via=html", etc.
- Filter out handled by nginx/non-django.

Static/Dynamic
----------
Port all html files to be served by Django.
- Take advantage of template inheritance.
    - Unify system currently split between Nginx SSI and Django templates.
- More direct way of logging traffic than possibly unreliable `watch_nginx.py`.

Templates
---------
Use context processors and `RequestContext` to add constants accessible in every template:
- https://stackoverflow.com/questions/433162/can-i-access-constants-in-settings-py-from-templates-in-django/433209#433209
