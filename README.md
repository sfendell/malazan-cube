# Malazan Cube of the Fallen

It's Malazan! Cube of the Fallen! Malazan, Book of the Fallen, but a Cube! MTG cube for you to play! Magic, the Gathering, just as ~~Richard Garfield~~ Steven Erikson intended!

**→ [Browse the cube](https://sfendell.github.io/malazan-cube/)**

---
Typical workflows:

There are three sources of truth to keep in sync:
- mse.set, the actual set that Magic Set Editor uses
- text, JSON representations of each card
- cards.json, a generated file you should never have to manually touch. It will be updated by [import_from|export_to]_text.py

- ** Editing in MSE **
  - Open mse-set with mse.exe and make edits you want
  - Run `export_to_text` and `export_to_image` to update text/ and export_cards files

- ** Editing in JSON **
  - Make whatever changes you want in the text/ directory to the cards
  - Run `import_from_text` and `export_to_image` to update mse.set and export_cards files

- ** Using Clippy **
  - Set your OPEN_API_KEY in your env
  - Run `mtg_clippy.py` to run every text file through MTG spell / grammar check
  - Run `import_from_text` and `export_to_image` to update mse.set and export_cards files

## What you need

- **Python 3**
- **Magic Set Editor** with the M15-style pack: `M15-Magic-Pack-main/mse.exe` in the **parent** of the repo
- For **import_from_text** / **export_to_text**: the set file `Malazan Cube of the Fallen.mse-set` in the repo root (for template or extraction)
- For **mtg_clippy**: `OPENAI_API_KEY` in your environment


After `export_to_image` (or `export_to_text`), commit `exported_cards/`, `cards.json`, and (if changed) `Malazan Cube of the Fallen.mse-set`, then push. A **GitHub Action** runs on push/PR and fails if **cards.json** is out of date with `text/` and `exported_cards/`, so you’re reminded to regenerate and commit it. The GitHub Pages gallery updates on the next deploy.
