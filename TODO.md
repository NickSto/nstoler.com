Notepad
-------

Redirect to `#bottom` on add/delete

Fix spacing between lines:
* on copy/paste, empty lines appear between every real one.
    - I think it's actually because each line is a `<p>` now.
* Maybe try just pasting the literal text, without `<p>`'s
    - Rely on white-space: pre-wrap to break lines.
