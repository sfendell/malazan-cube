#!/usr/bin/env python3
# Generate cards.json for GitHub Pages: card list with colors, type, and text for filtering.
# Reads the MSE set directly (parses set file from the zip); matches cards to exported_cards/*.png by name
# (normalized), not by index, since export order and set-file order can differ.
# Run from repo root. Called by finalize (after export_to_image).

import json
import re
import sys
from pathlib import Path

from mse_parse import (
    ROOT,
    parse_set_blocks,
    read_set_from_mse,
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


def mana_value_from_mse_cost(cost: str) -> int:
    """Converted mana value from MSE casting_cost string (e.g. 2WU, 1R/G, XGU)."""
    s = (cost or "").strip()
    if not s:
        return 0
    s = re.sub(r"<[^>]+>", "", s)
    s = s.upper().replace(" ", "")
    total = 0
    i = 0
    wubrg = frozenset("WUBRG")
    while i < len(s):
        c = s[i]
        if c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            total += int(s[i:j])
            i = j
            continue
        if c == "X":
            i += 1
            continue
        if c in wubrg:
            if i + 2 < len(s) and s[i + 1] == "/" and s[i + 2] in wubrg:
                total += 1
                i += 3
                continue
            total += 1
            i += 1
            continue
        i += 1
    return total


def normalize_name(s: str) -> str:
    """Lowercase, remove non-alphanumeric; for matching card name to image filename stem."""
    return re.sub(r"[^\w]", "", s).lower()


def image_sort_key(path: Path) -> tuple:
    """Order exports: Name.png before Name.1.png before Name.2.png (MSE duplicate names)."""
    stem = path.stem
    m = re.match(r"^(.+)\.(\d+)$", stem)
    if m:
        return (normalize_name(m.group(1)), int(m.group(2)))
    return (normalize_name(stem), 0)


def image_base_norm(stem: str) -> str:
    """Normalized card name for Food.1 / Child God.2 stems."""
    m = re.match(r"^(.+)\.\d+$", stem)
    return normalize_name(m.group(1) if m else stem)


def build_norm_to_img_list(image_files: list[Path]) -> dict[str, list[str]]:
    """Map normalized card name -> PNG filenames in export order (supports duplicate names)."""
    norm_to_imgs: dict[str, list[str]] = {}
    for p in sorted(image_files, key=image_sort_key):
        base = image_base_norm(p.stem)
        norm_to_imgs.setdefault(base, []).append(p.name)
    return norm_to_imgs


def main():
    if not MSE_SET_PATH.exists():
        print(f"MSE set not found: {MSE_SET_PATH}", file=sys.stderr)
        sys.exit(1)

    _, cards_content = read_set_from_mse(MSE_SET_PATH)
    parsed = list(parse_set_blocks(cards_content))

    # Match images by normalized card name; duplicate names use Name.png, Name.1.png, … in set order
    image_files = list(EXPORT_DIR.glob("*.png")) if EXPORT_DIR.exists() else []
    norm_to_imgs = build_norm_to_img_list(image_files)
    name_use_index: dict[str, int] = {}

    cards = []
    for card in parsed:
        name = (card.get("name") or "").strip()
        if not name:
            continue
        norm = normalize_name(name)
        imgs = norm_to_imgs.get(norm, [])
        idx = name_use_index.get(norm, 0)
        if idx >= len(imgs):
            continue
        img_name = imgs[idx]
        name_use_index[norm] = idx + 1
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
            "img": img_name,
            "colors": colors,
            "typeLine": type_line,
            "text": text,
            "manaValue": mana_value_from_mse_cost(cost),
        })

    cards.sort(key=lambda c: (c["name"] or "").lower())
    OUT_PATH.write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(cards)} card(s) to {OUT_PATH}")


if __name__ == "__main__":
    main()
