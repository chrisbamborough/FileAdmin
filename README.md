# Keyword File Organizer

A small desktop app that moves files into a destination folder based on a keyword in the filename.

## What it does

- Choose a source folder.
- Enter a keyword.
- Choose a destination folder.
- Click **Organize Files**.
- Files in the source whose names contain the keyword are moved to:
  - `<destination>/<keyword>/`

If a file with the same name already exists in the destination keyword folder, the app keeps both by renaming the moved file to `name_1.ext`, `name_2.ext`, and so on.

## Run the app

1. Open a terminal in this folder.
2. Run:

```bash
python3 app.py
```

Default startup uses terminal prompts so the app always responds immediately.

Optional modes:

```bash
python3 app.py --mac-dialog
python3 app.py --gui
python3 app.py --help
```

If your Python build does not include Tkinter, the app automatically switches to a fallback mode:

- Interactive CLI prompts are used by default.
- On macOS, you can opt into popup dialogs by running `python3 app.py --mac-dialog`.

If macOS popup dialogs are blocked by permissions or canceled, the app prints a fallback message and switches to terminal prompts.

## Notes

- By default, it searches inside subfolders of the source folder.
- Keyword matching is case-insensitive by default (can be changed in the app).
- The app moves files (does not copy).
- GUI mode requires Tkinter support in your Python installation.
