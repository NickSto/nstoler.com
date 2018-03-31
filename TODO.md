# Port from 1.0

Small utilities?
http://nstoler.com/misc/dataurl.html
http://nstoler.com/misc/urlconv.html

# Notepad

Allow non-admins to see `/notepad/monitor`.
- Only show pages they've edited.


## Editing notes

### HTML

Add a "select all" and "select none" button.
- Allows effectively renaming a page easily.
- Without JavaScript, will have to reload the page with "?select=all"

#### Buttons on each note
Add `<button>`s next to each note for `delete`, `edit`/`save`, `move up`, `move down`, and `move to a different page`
- Characters I can use: ✕, ✎/🖫, ↑, ↓
- Put them in the top-right, in a horizontal line, inside the area with the note text.
    - Hopefully the text can wrap around the buttons.
    - This is in order to still allow compact, one-line notes, but take as little horizontal space as possible on mobile.
- Fade out the buttons unless you `:hover`?
  - But on mobile..?
- Enclose each note in a `<form>`.
    - Use each `<button>`'s `value` attribute to communicate which action it's executing.
        - E.g. `<button name="action" value="edit">edit</button>`
            - This will send the key/value pair `action`: `edit` in the POST.
- The note can be in a `<textarea>`.
    - Remove the borders with CSS and it looks/acts just like a contenteditable element.
    - BUT: `<textarea>`s come with a pre-set height that doesn't change with the typed text.
        - Either have to:
            1. use JavaScript to dynamically re-size it or
            2. go back to a `contenteditable` `<pre>` and submit its contents via JavaScript.
        - Maybe I do some progressive enhancement:
            1. Without JavaScript the `edit` button just goes to the `editform` page where you edit and submit the text.
            2. With JavaScript it's a `save` button that does it all at once.
- JavaScript solutions:
    - Maybe mobile just won't work well without JavaScript.
    - Tap on a note to bring up the buttons.
- Some nice code for the buttons themselves:
```html
<div class="actions buttons">
  <button class="btn btn-default btn-xs" name="action" value="moveup">↑</button>
  <button class="btn btn-default btn-xs" name="action" value="movedown">↓</button>
  <button class="btn btn-default btn-xs" name="action" value="edit">✎</button>
  <button class="btn btn-default btn-xs" name="action" value="delete">✕</button>
</div>
```
- Looks like you can get the buttons to nicely float in the upper-right, with the text wrapping.
    - But not with a `<textarea>` or `<pre>`!
    - Have to put the buttons' `<div>` directly inside the `<div>` holding the text.

### View
Moving algorithm:
    1. Find the first note on the same page with a lower `display_order` (if moving up).
    2. Swap the `display_order`s of the two notes.


### Database
Use the `Move` model to keep a history of movement actions.
- Moving a note to a different page.
- Moving a note up or down the same page.


# Traffic

`watch_nginx.py`: Log every non-Django visit, but add flags for things like `handler` and `via`.

## Optional filters
- Try to filter out bots.
- Filter out `via=html`, etc.
- Filter out handled by nginx/non-django.

# Static/Dynamic

Port all html files to be served by Django.
- Take advantage of template inheritance.
    - Unify system currently split between Nginx SSI and Django templates.
- More direct way of logging traffic than possibly unreliable `watch_nginx.py`.

# Templates

Use context processors and `RequestContext` to add constants accessible in every template:
- https://stackoverflow.com/questions/433162/can-i-access-constants-in-settings-py-from-templates-in-django/433209#433209
