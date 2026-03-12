#!/usr/bin/env python3
# finalize: Regenerate exported_cards and cards.json from the .mse-set file.
# With no args: export all cards.
# With --cards 1 5 10: backup exported_cards, run full export, then restore previous
# images for every card whose collector number is not in the list (so only those
# cards get new PNGs). Used by mtg_clippy after it edits specific cards.

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from mse_parse import (
    EXTRACT_DIR,
    extract_mse_set,
    read_set_content,
    parse_set_blocks,
)

ROOT = Path(__file__).resolve().parent
MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
EXPORTED_DIR = ROOT / "exported_cards"
GENERATED = ROOT / "__generated__"
PREVIOUS_EXPORTED = GENERATED / "previous_exported_cards"
CARDS_JSON = ROOT / "cards.json"


def _name_to_collector() -> dict:
    """Parse set, return dict of card name -> collector number (1-based, alphabetical by name)."""
    extract_mse_set(MSE_SET_PATH, EXTRACT_DIR)
    _, cards_content = read_set_content(EXTRACT_DIR)
    cards = list(parse_set_blocks(cards_content))
    sorted_by_name = sorted(enumerate(cards), key=lambda x: (x[1].get("name") or "").strip().lower())
    return {(c.get("name") or "").strip(): cn for cn, (_, c) in enumerate(sorted_by_name, 1) if (c.get("name") or "").strip()}


def main():
    parser = argparse.ArgumentParser(description="Regenerate exported_cards and cards.json from the MSE set.")
    parser.add_argument(
        "--cards", "-c",
        type=int,
        nargs="*",
        metavar="N",
        help="Only refresh images for these collector numbers; others keep previous PNGs. Omit to export all.",
    )
    args = parser.parse_args()
    os.chdir(ROOT)

    if not MSE_SET_PATH.exists():
        print(f"MSE set not found: {MSE_SET_PATH}", file=sys.stderr)
        sys.exit(1)

    export_only_collectors = set(args.cards) if args.cards else None

    if export_only_collectors is not None:
        name_to_cn = _name_to_collector()
        GENERATED.mkdir(parents=True, exist_ok=True)
        if EXPORTED_DIR.exists():
            if PREVIOUS_EXPORTED.exists():
                shutil.rmtree(PREVIOUS_EXPORTED)
            PREVIOUS_EXPORTED.mkdir(parents=True)
            for p in EXPORTED_DIR.glob("*.png"):
                shutil.copy2(p, PREVIOUS_EXPORTED / p.name)
        print(f"Finalize: refreshing only collector numbers {sorted(export_only_collectors)} ({len(export_only_collectors)} card(s)).")

    print("\n=== export_to_image ===")
    r = subprocess.run([sys.executable, str(ROOT / "export_to_image.py")], cwd=str(ROOT))
    if r.returncode != 0:
        sys.exit(r.returncode)

    if export_only_collectors is not None and PREVIOUS_EXPORTED.exists() and CARDS_JSON.exists():
        cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
        restored = 0
        for c in cards:
            name = (c.get("name") or "").strip()
            img = c.get("img") or ""
            cn = name_to_cn.get(name)
            if name and img and cn is not None and cn not in export_only_collectors:
                src = PREVIOUS_EXPORTED / img
                if src.exists():
                    shutil.copy2(src, EXPORTED_DIR / img)
                    restored += 1
        if restored:
            print(f"Restored {restored} unchanged card image(s) from previous export.")

    print("\nfinalize done.")


if __name__ == "__main__":
    main()
