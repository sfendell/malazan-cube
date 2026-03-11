#!/usr/bin/env python3
# Generate cards.json for GitHub Pages: card list with colors, type, and text for filtering.
# Reads text/*.txt as JSON blobs; matches exported_cards/*.png. Run from repo root.

import json
import re
import sys
from pathlib import Path

WUBRG = list("WUBRG")
ROOT = Path(__file__).resolve().parent
TEXT_DIR = ROOT / "text"
EXPORT_DIR = ROOT / "exported_cards"
OUT_PATH = ROOT / "cards.json"


def get_colors_from_cost(cost: str) -> list:
    if not cost:
        return []
    return sorted(set(c.upper() for c in cost if c.upper() in WUBRG), key=lambda c: WUBRG.index(c))


def type_line_from_json(data: dict) -> str:
    """Build display type line from supertypes + types - subtypes."""
    supertypes = data.get("supertypes") or []
    types = data.get("types") or []
    subtypes = data.get("subtypes") or []
    first = " ".join(supertypes + types)
    second = " ".join(subtypes)
    if not second:
        return first
    return f"{first} - {second}"


def main():
    meta = {}
    if TEXT_DIR.exists():
        for f in sorted(TEXT_DIR.glob("*.txt")):
            try:
                content = f.read_text(encoding="utf-8")
                data = json.loads(content)
            except (json.JSONDecodeError, OSError):
                continue
            name = (data.get("name") or "").strip()
            if not name:
                continue
            cost = data.get("cost") or ""
            type_line = type_line_from_json(data)
            rule = (data.get("rule_text") or "").strip()
            flavor = (data.get("flavor_text") or "").strip()
            text = " ".join([rule, flavor]).strip()
            colors = get_colors_from_cost(cost)
            color_key = "".join(sorted(colors, key=lambda c: WUBRG.index(c)))
            meta[name] = {
                "colors": color_key,
                "typeLine": type_line,
                "text": text,
            }

    cards = []
    if EXPORT_DIR.exists():
        for p in sorted(EXPORT_DIR.glob("*.png")):
            img_name = p.name
            name = re.sub(r"\.png$", "", img_name, flags=re.I)
            m = meta.get(name, {})
            cards.append({
                "name": name,
                "img": img_name,
                "colors": m.get("colors", ""),
                "typeLine": m.get("typeLine", ""),
                "text": m.get("text", ""),
            })

    OUT_PATH.write_text(json.dumps(cards, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(cards)} cards to {OUT_PATH}")


if __name__ == "__main__":
    main()
