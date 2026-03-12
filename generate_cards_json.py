#!/usr/bin/env python3
# Generate cards.json for GitHub Pages: card list with colors, type, and text for filtering.
# Reads the MSE set directly (extracts and parses); matches by order to exported_cards/*.png.
# Run from repo root. Called by finalize (after export_to_image).

import json
import sys
from pathlib import Path

from mse_parse import (
    EXTRACT_DIR,
    ROOT,
    extract_mse_set,
    read_set_content,
    parse_set_blocks,
    strip_mse_markup,
    strip_type_markup,
    type_line_display,
)

WUBRG = list("WUBRG")
MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
EXPORT_DIR = ROOT / "exported_cards"
OUT_PATH = ROOT / "cards.json"


def get_colors_from_cost(cost: str) -> list:
    if not cost:
        return []
    return sorted(set(c.upper() for c in cost if c.upper() in WUBRG), key=lambda c: WUBRG.index(c))


def main():
    if not MSE_SET_PATH.exists():
        print(f"MSE set not found: {MSE_SET_PATH}", file=sys.stderr)
        sys.exit(1)

    ROOT.joinpath("__generated__").mkdir(parents=True, exist_ok=True)
    extract_mse_set(MSE_SET_PATH, EXTRACT_DIR)
    header, cards_content = read_set_content(EXTRACT_DIR)
    parsed = list(parse_set_blocks(cards_content))

    # Build meta from parsed cards (same order as set = same order as exported_cards)
    cards = []
    images = sorted(EXPORT_DIR.glob("*.png"), key=lambda p: p.name) if EXPORT_DIR.exists() else []
    for i, card in enumerate(parsed):
        name = (card.get("name") or "").strip()
        if not name or i >= len(images):
            continue
        cost = (card.get("casting_cost") or "").strip()
        super_type = strip_type_markup(card.get("super_type", ""))
        sub_type = strip_type_markup(card.get("sub_type", ""))
        type_line = type_line_display(super_type, sub_type)
        rule = strip_mse_markup(card.get("rule_text", ""), preserve_newlines=True).strip()
        flavor = strip_mse_markup(card.get("flavor_text", "")).strip()
        text = " ".join([rule, flavor]).strip()
        colors = "".join(sorted(get_colors_from_cost(cost), key=lambda c: WUBRG.index(c)))
        cards.append({
            "name": name,
            "img": images[i].name,
            "colors": colors,
            "typeLine": type_line,
            "text": text,
        })

    OUT_PATH.write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(cards)} card(s) to {OUT_PATH}")


if __name__ == "__main__":
    main()
