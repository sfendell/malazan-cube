#!/usr/bin/env python3
# One-off: Remove art/*.png that are duplicates of the canonical card name but missing punctuation.
# Canonical names from cards.json (or MSE set). Deletes any art file that normalizes to the same
# as a canonical but isn't the canonical filename.

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS_JSON = ROOT / "cards.json"
ART_DIR = ROOT / "art"
BAD_CHARS = r'\/:*?"<>|'


def get_safe_filename(name: str) -> str:
    for c in BAD_CHARS:
        name = name.replace(c, "_")
    return name.strip()


def normalize(s: str) -> str:
    """Lowercase, remove non-alphanumeric (so ' and , etc. removed)."""
    return re.sub(r"[^\w]", "", s).lower()


def main():
    if not CARDS_JSON.exists():
        print("cards.json not found; run finalize.py first or ensure cards.json exists.", file=sys.stderr)
        sys.exit(1)
    cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    card_names = [(c.get("name") or "").strip() for c in cards if (c.get("name") or "").strip()]

    canonical_filenames = {get_safe_filename(name) + ".png" for name in card_names}
    canonical_by_norm = {normalize(get_safe_filename(name)): get_safe_filename(name) + ".png" for name in card_names}

    to_remove = []
    for p in ART_DIR.glob("*.png"):
        if p.name in canonical_filenames:
            continue
        n = normalize(p.stem)
        if n in canonical_by_norm:
            to_remove.append(p)

    for p in to_remove:
        print(p.name)
        p.unlink()
    print(f"Removed {len(to_remove)} duplicate art file(s).")


if __name__ == "__main__":
    main()
