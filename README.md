# Malazan Cube of the Fallen

It's Malazan! Cube of the Fallen! Malazan, Book of the Fallen, but a Cube! MTG cube for yo to play! Magic, the Gathering, just as ~~Richard Garfield~~ Steven Erikson intended!

**→ [Browse the cube](https://sfendell.github.io/malazan-cube/)**

---

## Rendering cards

Card art and text live in this repo; rendered PNGs are produced by **Magic Set Editor (MSE)** and the scripts here.

### What you need

- **PowerShell** (Windows)
- **Magic Set Editor** with the M15-style pack (the repo expects `M15-Magic-Pack-main\mse.exe` relative to the repo root, and the set file `Malazan Cube of the Fallen.mse-set`)
- **mse-extract/** — the contents of the `.mse-set` file unzipped (so that `mse-extract/set` and the image files exist)

### Commands

1. **Fix wording** (optional) — Run the clippy script to normalize ability text in `text/` using an LLM. Requires `OPENAI_API_KEY` in your environment.
   ```powershell
   .\mtg-clippy.ps1
   ```

2. **Render all cards** — Sync every `text/*.txt` into the MSE set, repack the set, export PNGs to `exported_cards/`, and regenerate `cards.json` for the site.
   ```powershell
   .\render-all-cards.ps1
   ```
   When it finishes, commit the updated `exported_cards/`, `cards.json`, and (if you changed it) `Malazan Cube of the Fallen.mse-set`, then push. The GitHub Pages site will show the new cards after the next deploy.

### GitHub Pages

To host the gallery yourself: **Settings → Pages → Deploy from a branch** → branch **main**, folder **/ (root)**. The site will be at `https://<your-username>.github.io/malazan-cube/`.
