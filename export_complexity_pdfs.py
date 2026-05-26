#!/usr/bin/env python3
# export_complexity_pdfs: Rank draftable cube cards by complexity, pick the top 150,
# randomly split into three groups of 50, and write one printable PDF per group
# plus a text manifest. Excludes tokens, Fatids, Deck of Dragons, Quick Ben's Souls,
# and flip-card backs (backs are included adjacent to their front in PDFs).

import argparse
import json
import random
import re
import sys
from pathlib import Path

from export_to_draftmancer import (
    DECK_OF_DRAGONS_NAMES,
    QUICK_BENS_SOULS_NAMES,
    build_flip_lookup,
    flip_backs_to_exclude,
    is_token_card,
    normalize_name,
    load_flip_map,
)
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
OUT_DIR = ROOT / "complex_cards"
MANIFEST = OUT_DIR / "complexity-groups.txt"

COMPLEX_KEYWORDS = [
    "choose",
    "whenever",
    "at the beginning",
    "at the end",
    "if you",
    "if a",
    "if an",
    "transform",
    "ascend",
    "copy",
    "exile",
    "counter",
    "proliferate",
    "investigate",
    "tutor",
    "search your library",
    "return target",
    "sacrifice",
    "gain control",
    "each opponent",
    "each player",
    "instead",
    "unless",
    " may ",
    "target",
    "where x",
    "equal to",
    "less than",
    "greater than",
    "additional",
    "prevent",
    "replace",
    "win the game",
    "lose the game",
    "elderstorm",
    "slow",
    "oncebound",
    "behold",
    "plunder",
    "cunning",
    "populate",
    "amass",
    "modal",
    "repeat",
    "for each",
    "x is",
    "you may",
]


def is_fatid(card: dict) -> bool:
    return "fatid" in (card.get("typeLine") or "").lower()


def complexity_score(text: str, type_line: str, mana_value: int) -> float:
    blob = f"{text} {type_line}".lower()
    words = len(re.findall(r"[A-Za-z']+", text))
    chars = len(text)
    lines = text.count("\n") + (1 if text.strip() else 0)
    keyword_hits = sum(blob.count(kw) for kw in COMPLEX_KEYWORDS)
    clauses = len(re.findall(r"[.!?]", text)) + text.count("\n")

    type_bonus = 0.0
    tl = type_line.lower()
    if "planeswalker" in tl:
        type_bonus += 20
    if "legendary" in tl:
        type_bonus += 4
    if "kindred" in tl:
        type_bonus += 2
    if "artifact" in tl and "creature" not in tl:
        type_bonus += 2

    return (
        words * 1.0
        + chars * 0.04
        + lines * 6
        + keyword_hits * 5
        + clauses * 3
        + mana_value * 1.5
        + type_bonus
    )


def score_card(
    card: dict,
    cards_by_norm: dict[str, dict],
    flip_map: dict[str, str],
) -> float:
    text = card.get("text") or ""
    type_line = card.get("typeLine") or ""
    back_name = flip_map.get(card["name"])
    if back_name:
        back = cards_by_norm.get(normalize_name(back_name))
        if back:
            text = f"{text}\n{back.get('text') or ''}".strip()
            type_line = f"{type_line} {back.get('typeLine') or ''}".strip()
    return complexity_score(text, type_line, card.get("manaValue") or 0)


def draftable_pool(
    cards: list[dict],
    flip_map: dict[str, str],
) -> list[dict]:
    undraftable_norm = {normalize_name(n) for n in DECK_OF_DRAGONS_NAMES + QUICK_BENS_SOULS_NAMES}
    flip_back_norm = {normalize_name(n) for n in flip_backs_to_exclude(flip_map)}

    pool = []
    for card in cards:
        if is_token_card(card) or is_fatid(card):
            continue
        norm = normalize_name(card["name"])
        if norm in undraftable_norm or norm in flip_back_norm:
            continue
        if not (card.get("text") or "").strip():
            continue
        pool.append(card)
    return pool


def rank_cards(
    pool: list[dict],
    cards_by_norm: dict[str, dict],
    flip_map: dict[str, str],
) -> list[tuple[dict, float]]:
    ranked = [(card, score_card(card, cards_by_norm, flip_map)) for card in pool]
    ranked.sort(key=lambda item: (-item[1], (item[0].get("name") or "").lower()))
    return ranked


def random_groups(ranked: list[tuple[dict, float]], *, seed: int | None) -> list[list[tuple[dict, float]]]:
    top = list(ranked[:150])
    rng = random.Random(seed)
    rng.shuffle(top)
    return [top[i : i + 50] for i in range(0, 150, 50)]


def expand_for_pdf(
    group: list[tuple[dict, float]],
    flip_map: dict[str, str],
    cards_by_norm: dict[str, dict],
) -> list[dict]:
    """Front face first, flip back immediately after when applicable."""
    pdf_cards: list[dict] = []
    for card, _ in group:
        pdf_cards.append(card)
        back_name = flip_map.get(card["name"])
        if not back_name:
            continue
        back = cards_by_norm.get(normalize_name(back_name))
        if back:
            pdf_cards.append(back)
    return pdf_cards


def write_manifest(
    groups: list[list[tuple[dict, float]]],
    flip_map: dict[str, str],
    *,
    seed: int | None,
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "Malazan Cube — 150 most complex draftable cards",
        "Excluded: tokens, Fatids, Deck of Dragons, Quick Ben's Souls, flip-card backs.",
        "Top 150 by complexity score, then randomly shuffled into three groups of 50.",
        f"Random seed: {seed if seed is not None else '(none)'}",
        "",
    ]
    for i, group in enumerate(groups, 1):
        lines.append(f"Group {i}")
        lines.append("-" * 7)
        for j, (card, score) in enumerate(group, 1):
            back_name = flip_map.get(card["name"])
            suffix = f"  (+ flip back: {back_name})" if back_name else ""
            lines.append(f"{j:2}. {card['name']}  (score {score:.0f}){suffix}")
        lines.append("")
    MANIFEST.write_text("\n".join(lines), encoding="utf-8")


def write_pdf(cards: list[dict], output: Path) -> None:
    card_w_px = inches_to_px(CARD_W_IN)
    card_h_px = inches_to_px(CARD_H_IN)
    page_w_px = inches_to_px(PAGE_W_IN)
    page_h_px = inches_to_px(PAGE_H_IN)
    cols, rows, margin_x, margin_y = layout_grid(page_w_px, page_h_px, card_w_px, card_h_px)

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
        raise RuntimeError(f"No pages generated for {output.name}")

    output.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        output,
        "PDF",
        save_all=True,
        append_images=pages[1:],
        resolution=DPI,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the 150 most complex draftable cards as three random PDF groups.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for shuffling into groups (default: 42)",
    )
    args = parser.parse_args()

    if not CARDS_JSON.exists():
        print(f"Missing {CARDS_JSON}", file=sys.stderr)
        sys.exit(1)
    if not EXPORT_DIR.exists():
        print(f"Missing {EXPORT_DIR}; run finalize.py first.", file=sys.stderr)
        sys.exit(1)

    cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    flip_map = build_flip_lookup(load_flip_map(), cards)
    cards_by_norm = {normalize_name(c["name"]): c for c in cards}

    pool = draftable_pool(cards, flip_map)
    ranked = rank_cards(pool, cards_by_norm, flip_map)
    if len(ranked) < 150:
        print(
            f"Only {len(ranked)} draftable scorable cards found; need 150.",
            file=sys.stderr,
        )
        sys.exit(1)

    groups = random_groups(ranked, seed=args.seed)
    write_manifest(groups, flip_map, seed=args.seed)

    pdf_names = [
        OUT_DIR / "complex-group-1.pdf",
        OUT_DIR / "complex-group-2.pdf",
        OUT_DIR / "complex-group-3.pdf",
    ]
    for pdf_path, group in zip(pdf_names, groups):
        pdf_cards = expand_for_pdf(group, flip_map, cards_by_norm)
        write_pdf(pdf_cards, pdf_path)
        flip_backs = len(pdf_cards) - len(group)
        extra = f" + {flip_backs} flip back(s)" if flip_backs else ""
        print(f"Wrote {pdf_path} ({len(group)} picks{extra}, {len(pdf_cards)} card images)")

    print(f"Wrote manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
