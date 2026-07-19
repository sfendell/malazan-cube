#!/usr/bin/env python3
# export_token_sheets: One US Letter page per token, 3x3 = 9 identical copies.
# Print and cut for physical tokens. Run from repo root:
#   python export_token_sheets.py

import argparse
import json
import sys
from pathlib import Path

from export_to_draftmancer import is_token_card
from export_to_pdf import (
    CARD_H_IN,
    CARD_W_IN,
    DPI,
    PAGE_H_IN,
    PAGE_W_IN,
    build_pages,
    inches_to_px,
    layout_grid,
)

ROOT = Path(__file__).resolve().parent
CARDS_JSON = ROOT / "cards.json"
EXPORT_DIR = ROOT / "exported_cards"
DEFAULT_OUT = ROOT / "malazan-token-sheets.pdf"

COPIES_PER_PAGE = 9


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export token print sheets: 9 identical copies of each token per page.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output PDF path (default: {DEFAULT_OUT.name})",
    )
    args = parser.parse_args()

    if not CARDS_JSON.exists():
        print(f"Missing {CARDS_JSON}", file=sys.stderr)
        sys.exit(1)
    if not EXPORT_DIR.exists():
        print(f"Missing {EXPORT_DIR}; run finalize.py first.", file=sys.stderr)
        sys.exit(1)

    with CARDS_JSON.open(encoding="utf-8") as f:
        cards = json.load(f)

    tokens = [c for c in cards if is_token_card(c)]
    tokens.sort(key=lambda c: ((c.get("name") or "").lower(), c.get("img") or ""))

    if not tokens:
        print("No tokens found in cards.json.", file=sys.stderr)
        sys.exit(1)

    # Expand each token to 9 copies so build_pages fills one page per token.
    expanded = [t for t in tokens for _ in range(COPIES_PER_PAGE)]

    card_w_px = inches_to_px(CARD_W_IN)
    card_h_px = inches_to_px(CARD_H_IN)
    page_w_px = inches_to_px(PAGE_W_IN)
    page_h_px = inches_to_px(PAGE_H_IN)
    cols, rows, margin_x, margin_y = layout_grid(page_w_px, page_h_px, card_w_px, card_h_px)
    per_page = cols * rows
    if per_page != COPIES_PER_PAGE:
        print(
            f"Expected {COPIES_PER_PAGE} slots/page, got {cols}x{rows}={per_page}.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Layout: {cols}x{rows} = {per_page} copies/page "
        f"at {CARD_W_IN}\"x{CARD_H_IN}\" on {PAGE_W_IN}\"x{PAGE_H_IN}\" @ {DPI} DPI"
    )
    print(f"Tokens: {len(tokens)} -> {len(tokens)} page(s)")

    pages = build_pages(
        expanded,
        EXPORT_DIR,
        card_w_px,
        card_h_px,
        page_w_px,
        page_h_px,
        cols,
        rows,
        margin_x,
        margin_y,
    )
    if not pages:
        print("No pages generated.", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        args.output,
        "PDF",
        save_all=True,
        append_images=pages[1:],
        resolution=DPI,
    )
    print(f"Wrote {args.output} ({len(pages)} page(s)).")


if __name__ == "__main__":
    main()
