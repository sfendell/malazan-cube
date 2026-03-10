#!/usr/bin/env python3
# Generate cards.json for GitHub Pages: card list with colors, type, and text for filtering.
# Reads text/*.txt for metadata and matches exported_cards/*.png. Run from repo root.

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


def main():
    meta = {}
    if TEXT_DIR.exists():
        for f in sorted(TEXT_DIR.glob("*.txt")):
            content = f.read_text(encoding="utf-8")
            lines = content.replace("\r", "").rstrip().split("\n")
            name = lines[0].strip() if lines else ""
            cost = None
            type_line = None
            text_lines = []
            past_blank = False
            for i in range(1, len(lines)):
                line = lines[i]
                t = line.strip()
                m = re.match(r"^Cost:\s*(.*)$", line)
                if m:
                    cost = m.group(1).strip()
                    continue
                m = re.match(r"^Type:\s*(.*)$", line)
                if m:
                    type_line = m.group(1).strip()
                    continue
                if re.match(r"^P/T:", line):
                    continue
                if re.match(r"^\s*$", line):
                    past_blank = True
                    continue
                if past_blank:
                    text_lines.append(t)
            colors = get_colors_from_cost(cost or "")
            color_key = "".join(sorted(colors, key=lambda c: WUBRG.index(c)))
            meta[name] = {
                "colors": color_key,
                "typeLine": (type_line or "").strip(),
                "text": " ".join(text_lines).strip(),
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
