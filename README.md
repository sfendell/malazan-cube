# Malazan Cube of the Fallen

It's Malazan! Cube of the Fallen! Malazan, Book of the Fallen, but a Cube! MTG cube for you to play! Magic, the Gathering, just as ~~Richard Garfield~~ Steven Erikson intended!

**→ [Browse the cube](https://sfendell.github.io/malazan-cube/)**

---

## Scripts

Card data lives in **text/** (one `.txt` per card) and **art/** (one image per card). The **MSE set** (`Malazan Cube of the Fallen.mse-set`) and **exported_cards/** (PNGs for the gallery) are generated from these. All intermediary files go in **__generated__/** (gitignored).

| Script | Purpose |
|--------|--------|
| **mtg_clippy** | LLM wording/grammar fix for MTG ability text. **Only** reads/writes files in **text/**. Writes changed-card list to `__generated__/clippy-changed.txt`. |
| **export_to_text** | Rebuild **text/** from the MSE set. Extracts the `.mse-set` into `__generated__`, parses the set file, and overwrites `text/*.txt`. |
| **import_from_text** | Build the **.mse-set** from **text/** and **art/**. Uses `__generated__/mse-extract` for unpack/repack, then overwrites `Malazan Cube of the Fallen.mse-set`. |
| **export_to_image** | Rebuild **exported_cards/** from the MSE set (MSE `--export-images`). Then regenerates **cards.json** for the site. |

Typical workflows:

- **MSE set is source of truth**  
  `export_to_text` → edit in `text/` (optionally `mtg_clippy`) → `import_from_text` → `export_to_image`

- **Text + art is source of truth**  
  Edit `text/` and `art/` → `import_from_text` → `export_to_image`


## What you need

- **Python 3**
- **Magic Set Editor** with the M15-style pack: `M15-Magic-Pack-main/mse.exe` in the **parent** of the repo
- For **import_from_text** / **export_to_text**: the set file `Malazan Cube of the Fallen.mse-set` in the repo root (for template or extraction)
- For **mtg_clippy**: `OPENAI_API_KEY` in your environment

## Commands

```bash
# Fix wording in text/ only (optional)
python mtg_clippy.py

# Recreate text/ from the MSE set
python export_to_text.py

# Build .mse-set from text/ and art/
python import_from_text.py

# Recreate exported_cards/ and cards.json from the MSE set
python export_to_image.py
```

After `export_to_image`, commit `exported_cards/`, `cards.json`, and (if changed) `Malazan Cube of the Fallen.mse-set`, then push. The GitHub Pages gallery will update on the next deploy.

## GitHub Pages

**Settings → Pages → Deploy from a branch** → branch **main**, folder **/ (root)**. Site: `https://<your-username>.github.io/malazan-cube/`.
