Port from 1.0
--------

Small utilities?
http://nstoler.com/misc/dataurl.html
http://nstoler.com/misc/urlconv.html

Notepad
-------

Allow non-admins to see `/notepad/monitor`.
- Only show pages they've edited.


### Editing notes

#### HTML
Add buttons next to each note for `delete`, `edit`, `↑`, and `↓`.
- In order of increasing difficulty.
- Fade out the buttons unless you `:hover`.
- Probably have to make an independent `<form>` for each.
    - Can't have different buttons in the same form perform different actions.
- The note can be in a `<textarea>`.
    - Remove the borders with CSS and it looks/acts just like a contenteditable element.
    - Will have to enclose the `<textarea>` and `edit` button in the same `<form>`.

#### Database
Add a pointer to the previous version of the note.
Add a `display_order` attribute to `Note`.
- Allowing editing of notes is great, but w/o this, the edited note will appear to jump to the bottom.
- The `move` buttons will edit this. Algorithm:
    1. Find the first note on the same page with a lower `display_order` (if moving up).
    2. Swap the `display_order`s of the two notes.


Traffic
-------

`watch_nginx.py`: Log every non-Django visit, but add flags for things like `handler` and `via`.

### Optional filters
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
