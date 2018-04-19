# Home page

## Make it dynamic?

Instead of the info getting outdated because it's a pain to change, store it in the database and present "edit" buttons to me.

Don't have to go nuts making it completely changeable, but I could store the text for each bit in the database. I could even allow adding/deleting entries from each main section ("Work", "Web Projects").

To avoid mistakes of the past (see: instawiki), I should explicitly only allow editing text, not the structure of the html (aside from a special feature for adding the above list entries). If I want to change the structure or display, that's when I go in and edit the html template, test it, commit it, and push it up.

### Caching

This would be a good time to invest in caching.
- The page doesn't change often, so I can set long TTLs.
- Avoiding a trip to the database would eliminate a lot of latency.
- BUT: This would probably prevent visits from being logged.


### Implementation

I'll just store each bit of text keyed by an identifier. Yes, this is what NoSQL was made for, but I'm not making a whole dependency on that just for this one thing.
- One table, two columns: key and text.
- The identifier should be general, not specific to one page structure.
  - "about-me", not "jumbotron-aside"

How to handle links? I need to be able to easily write them, as well as other little markup like italics. But I don't want to accept and inject raw html, even from an authenticated user.
- Use a subset of markdown?

Saving edit history
- I'd like to have a record of past versions of the text.
- I could use the same methods as with Notepad, with a `deleted` and `last_version` attribute.
  - Hell, I could actually use the Notepad infrastructure.
    - Would need to add an attribute to store the key for each bit of text.
    - Could actually use the special page name "", which is actually kind of accurate.
  - Okay, so maybe I store the text as Notepad notes, but it's probably still a good idea to make some custom models for this system.
    - The custom models would store the key, and point to a Notepad `Note`.

Models
- A generic `Text` object, storing a key and a reference to a Notepad `Note`.
  - Nothing more fancy or specialized, except the list stuff below.
- A `List` for each list of things.
  - A `ListItem` for each item in the list.
    - Store the item title separately or just use markdown (`##`) to indicate it?
      - If stored separately, probably should be stored in its own Note.
        - So I don't have to specially code version history stuff for it.
    - Have an attribute for special things like the [PDF] notation?
- Something to store meta-history, like `Move` in Notepad.
  - Track when I add, remove, or reorder a `List` or `ListItem`.

# Notepad

Allow non-admins to see `/notepad/monitor`.
- Only show pages they've edited.

Add `History` object to track the entire history of a note and its edited/moved forms.


## Editing notes

### Features

Add an "undo" button after moving notes up or down.
- Use the Move objects to know what to undo.
- How to tell the "view" view to show the undo, and what to undo?
  - Option 1: Add a undo= query parameter.
    - Value is a list of Move ids.
  - Option 2: Allow a POST to the "view" view?
    - Send Move ids as a POST parameter.

### HTML

Icons/characters for buttons
- Too many platform-specific issues
- Best to use actual icons (images)
- In case it's useful: 🖫

#### Buttons on each note
Add `<button>`s next to each note for `delete`, `edit`/`save`, `move up`, `move down`, and `move to a different page`
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
