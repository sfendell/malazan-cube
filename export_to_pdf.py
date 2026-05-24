#!/usr/bin/env python3
# export_to_pdf: Build a print-ready PDF of every card in cards.json at standard MTG size.
# US Letter (8.5" x 11"): 3 x 3 = 9 cards per page, 2.5" x 3.5" each, centered margins.
# Run from repo root: python export_to_pdf.py

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
CARDS_JSON = ROOT / "cards.json"
EXPORT_DIR = ROOT / "exported_cards"
DEFAULT_OUT = ROOT / "malazan-cube-printable.pdf"

# Standard tournament MTG card size (inches)
CARD_W_IN = 2.5
CARD_H_IN = 3.5

# US Letter
PAGE_W_IN = 8.5
PAGE_H_IN = 11.0

DPI = 300


def inches_to_px(inches: float) -> int:
    return round(inches * DPI)


def layout_grid(page_w_px: int, page_h_px: int, card_w_px: int, card_h_px: int) -> tuple[int, int, int, int]:
    """Return cols, rows, margin_x, margin_y for centered grid."""
    cols = page_w_px // card_w_px
    rows = page_h_px // card_h_px
    if cols < 1 or rows < 1:
        raise ValueError(
            f"Page ({page_w_px}x{page_h_px}px) is smaller than one card ({card_w_px}x{card_h_px}px)."
        )
    used_w = cols * card_w_px
    used_h = rows * card_h_px
    margin_x = (page_w_px - used_w) // 2
    margin_y = (page_h_px - used_h) // 2
    return cols, rows, margin_x, margin_y


def load_card_image(path: Path, card_w_px: int, card_h_px: int) -> Image.Image:
    with Image.open(path) as src:
        img = src.convert("RGB")
    if img.size != (card_w_px, card_h_px):
        img = img.resize((card_w_px, card_h_px), Image.Resampling.LANCZOS)
    return img


def build_pages(
    cards: list[dict],
    export_dir: Path,
    card_w_px: int,
    card_h_px: int,
    page_w_px: int,
    page_h_px: int,
    cols: int,
    rows: int,
    margin_x: int,
    margin_y: int,
) -> list[Image.Image]:
    per_page = cols * rows
    pages: list[Image.Image] = []
    page: Image.Image | None = None
    slot = 0

    for card in cards:
        img_name = card.get("img")
        if not img_name:
            print(f"Warning: no img for {card.get('name', '?')}, skipping.", file=sys.stderr)
            continue
        img_path = export_dir / img_name
        if not img_path.exists():
            print(f"Warning: missing {img_path}, skipping.", file=sys.stderr)
            continue

        if slot == 0:
            page = Image.new("RGB", (page_w_px, page_h_px), "white")
            pages.append(page)

        col = slot % cols
        row = slot // cols
        x = margin_x + col * card_w_px
        y = margin_y + row * card_h_px
        page.paste(load_card_image(img_path, card_w_px, card_h_px), (x, y))
        slot += 1
        if slot >= per_page:
            slot = 0

    return pages


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export all cube cards to a print-ready PDF at standard MTG card size.",
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

    card_w_px = inches_to_px(CARD_W_IN)
    card_h_px = inches_to_px(CARD_H_IN)
    page_w_px = inches_to_px(PAGE_W_IN)
    page_h_px = inches_to_px(PAGE_H_IN)
    cols, rows, margin_x, margin_y = layout_grid(page_w_px, page_h_px, card_w_px, card_h_px)
    per_page = cols * rows

    print(
        f"Layout: {cols}x{rows} = {per_page} cards/page "
        f"at {CARD_W_IN}\"x{CARD_H_IN}\" on {PAGE_W_IN}\"x{PAGE_H_IN}\" @ {DPI} DPI"
    )
    print(f"Cards: {len(cards)} -> {(len(cards) + per_page - 1) // per_page} page(s)")

    pages = build_pages(
        cards,
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
