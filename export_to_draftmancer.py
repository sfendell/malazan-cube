#!/usr/bin/env python3
# export_to_draftmancer: Build a Draftmancer custom card list from cards.json + MSE set.
# Draftable non-token cards become CustomCards with image URLs; output is a simple cube list.
# Run from repo root after exported_cards/ and cards.json are up to date (finalize.py).

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

from mse_parse import (
    parse_set_blocks,
    read_set_from_mse,
    strip_mse_markup,
    strip_type_markup,
    type_line_display,
)

ROOT = Path(__file__).resolve().parent
MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
CARDS_JSON = ROOT / "cards.json"
FLIP_JSON = ROOT / "flip-cards.json"
DEFAULT_OUT = ROOT / "draftmancer-cube.txt"
DEFAULT_IMAGE_BASE = "https://sfendell.github.io/malazan-cube/exported_cards/"

DECK_OF_DRAGONS_NAMES = [
    "Builder of High House Life",
    "Hunter of High House War",
    "King of High House Death",
    "Knight of High House Chains",
    "Magi of High House Chains",
    "Magi of High House Dark",
    "Mercenary of High House War",
    "Name to the Pantheon",
    "Priest of High House Light",
    "Queen of High House Shadow",
    "Scepter, Orb, and Throne",
    "The Obelisk",
    "Weaver of High House Life",
]

QUICK_BENS_SOULS_NAMES = [
    "Quick Ben, Burn's Adept",
    "Quick Ben, Denul Healer",
    "Quick Ben, Emurlahn Heretic",
    "Quick Ben, Hood's Disciple",
    "Quick Ben, Imperial Investigator",
    "Quick Ben, Ruse Master",
    "Quick Ben, Squad Mage",
    "Quick Ben, Tellan Wizard",
]

WUBRG = list("WUBRG")


def normalize_name(s: str) -> str:
    return re.sub(r"[^\w]", "", s).lower()


def is_token_card(card: dict) -> bool:
    t = (card.get("typeLine") or "").strip().lower()
    return t.startswith("token") or " token" in t


def mse_cost_to_scryfall(cost: str) -> str:
    cost = re.sub(r"<[^>]+>", "", (cost or "").strip())
    if not cost:
        return ""
    parts: list[str] = []
    i = 0
    wubrg = frozenset("WUBRG")
    while i < len(cost):
        c = cost[i]
        if c.isdigit():
            j = i
            while j < len(cost) and cost[j].isdigit():
                j += 1
            parts.append("{" + cost[i:j] + "}")
            i = j
            continue
        if c == "X":
            parts.append("{X}")
            i += 1
            continue
        if c in wubrg:
            if i + 2 < len(cost) and cost[i + 1] == "/" and cost[i + 2] in wubrg:
                parts.append("{" + c + "/" + cost[i + 2] + "}")
                i += 3
                continue
            parts.append("{" + c + "}")
            i += 1
            continue
        i += 1
    return "".join(parts)


def parse_type_line_fields(type_line: str) -> tuple[str, list[str]]:
    line = (type_line or "").strip()
    if " - " in line:
        main, sub = line.split(" - ", 1)
        return main.strip(), [s for s in sub.split() if s]
    return line, []


def colors_array(colors: str) -> list[str]:
    c = (colors or "").strip().upper()
    return [ch for ch in c if ch in WUBRG]


def image_url(base: str, filename: str) -> str:
    return base.rstrip("/") + "/" + quote(filename, safe="/")


def flip_backs_to_exclude(flip_map: dict[str, str]) -> set[str]:
    """Back faces and secondary sides of mutual flip pairs stay out of the draft pool."""
    exclude: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for front, back in flip_map.items():
        if back in flip_map and flip_map[back] == front:
            pair = tuple(sorted([front, back], key=str.lower))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            exclude.add(back)
        else:
            exclude.add(back)
    return exclude


def build_mse_lookup() -> dict[str, dict]:
    """Map normalized card name -> MSE fields (cost, power, toughness)."""
    if not MSE_SET_PATH.exists():
        return {}
    _, cards_content = read_set_from_mse(MSE_SET_PATH)
    lookup: dict[str, dict] = {}
    for card in parse_set_blocks(cards_content):
        name = (card.get("name") or "").strip()
        if not name:
            continue
        lookup[normalize_name(name)] = {
            "name": name,
            "casting_cost": (card.get("casting_cost") or "").strip(),
            "power": (card.get("power") or "").strip(),
            "toughness": (card.get("toughness") or "").strip(),
            "super_type": strip_type_markup(card.get("super_type", "")),
            "sub_type": strip_type_markup(card.get("sub_type", "")),
            "rule_text": strip_mse_markup(card.get("rule_text", ""), preserve_newlines=True).strip(),
            "flavor_text": strip_mse_markup(card.get("flavor_text", "")).strip(),
        }
    return lookup


def build_flip_lookup(flip_map: dict[str, str], cards: list[dict]) -> dict[str, str]:
    """Normalize flip map keys/values so name punctuation differences still match."""
    lookup: dict[str, str] = {}
    norm_to_canonical = {normalize_name(card["name"]): card["name"] for card in cards}
    for front, back in flip_map.items():
        front_name = norm_to_canonical.get(normalize_name(front), front)
        back_name = norm_to_canonical.get(normalize_name(back), back)
        lookup[front_name] = back_name
    return lookup


def resolve_name(name: str, cards_by_norm: dict[str, dict]) -> dict | None:
    return cards_by_norm.get(normalize_name(name))


def build_card_face(
    card: dict,
    mse: dict | None,
    image_base: str,
) -> dict:
    type_main, subtypes = parse_type_line_fields(card.get("typeLine", ""))
    mse = mse or {}
    oracle = (card.get("text") or "").strip()
    if not oracle:
        mse_text = mse.get("rule_text", "")
        flavor = mse.get("flavor_text", "")
        oracle = "\n".join(x for x in [mse_text, flavor] if x).strip()
    face: dict = {
        "name": card["name"],
        "type": type_main or type_line_display(mse.get("super_type", ""), mse.get("sub_type", "")),
        "image": image_url(image_base, card["img"]),
    }
    mana_cost = mse_cost_to_scryfall(mse.get("casting_cost", ""))
    face["mana_cost"] = mana_cost
    if subtypes:
        face["subtypes"] = subtypes
    colors = colors_array(card.get("colors", ""))
    if colors:
        face["colors"] = colors
    if oracle:
        face["oracle_text"] = oracle
    power = mse.get("power", "")
    toughness = mse.get("toughness", "")
    if power:
        face["power"] = power
    if toughness:
        face["toughness"] = toughness
    return face


def build_custom_card(
    card: dict,
    mse_lookup: dict[str, dict],
    flip_map: dict[str, str],
    cards_by_norm: dict[str, dict],
    image_base: str,
) -> dict:
    mse = mse_lookup.get(normalize_name(card["name"]))
    custom = build_card_face(card, mse, image_base)
    back_name = flip_map.get(card["name"])
    if back_name:
        back_card = resolve_name(back_name, cards_by_norm)
        if back_card:
            back_mse = mse_lookup.get(normalize_name(back_name))
            custom["layout"] = "flip"
            custom["back"] = build_card_face(back_card, back_mse, image_base)
    return custom


def load_cards() -> list[dict]:
    if not CARDS_JSON.exists():
        print(f"cards.json not found: {CARDS_JSON}", file=sys.stderr)
        sys.exit(1)
    return json.loads(CARDS_JSON.read_text(encoding="utf-8"))


def load_flip_map() -> dict[str, str]:
    if not FLIP_JSON.exists():
        return {}
    return json.loads(FLIP_JSON.read_text(encoding="utf-8"))


def draftable_cards(cards: list[dict], flip_map: dict[str, str]) -> list[dict]:
    undraftable_norm = {normalize_name(n) for n in DECK_OF_DRAGONS_NAMES + QUICK_BENS_SOULS_NAMES}
    flip_exclude_norm = {normalize_name(n) for n in flip_backs_to_exclude(flip_map)}

    draftable = []
    for card in cards:
        if is_token_card(card):
            continue
        norm = normalize_name(card["name"])
        if norm in undraftable_norm or norm in flip_exclude_norm:
            continue
        draftable.append(card)
    draftable.sort(key=lambda c: (c.get("name") or "").lower())
    return draftable


def render_draftmancer(
    custom_cards: list[dict],
    sheet_names: list[str],
    *,
    cube_name: str,
    boosters_per_player: int,
) -> str:
    settings = {
        "name": cube_name,
        "boostersPerPlayer": boosters_per_player,
        "withReplacement": False,
        "duplicateProtection": True,
        "colorBalance": False,
    }
    lines = [
        "# Malazan Cube of the Fallen — Draftmancer custom card list",
        "# Upload this file at https://draftmancer.com/",
        "# Card images must be reachable at the configured image base URL (GitHub Pages by default).",
        "",
        "[CustomCards]",
        json.dumps(custom_cards, indent="\t", ensure_ascii=False),
        "",
        "[Settings]",
        json.dumps(settings, indent="\t", ensure_ascii=False),
        "",
        "[DefaultSheet]",
    ]
    lines.extend(sheet_names)
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the Malazan cube as a Draftmancer custom card list.",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output file path (default: {DEFAULT_OUT.name})",
    )
    parser.add_argument(
        "--image-base-url",
        default=DEFAULT_IMAGE_BASE,
        help="Base URL for exported_cards PNGs (must be publicly reachable by Draftmancer)",
    )
    parser.add_argument(
        "--boosters",
        type=int,
        default=3,
        metavar="N",
        help="Default boosters per player in Draftmancer (default: 3)",
    )
    parser.add_argument(
        "--name",
        default="Malazan Cube of the Fallen",
        help="Cube name shown in Draftmancer",
    )
    args = parser.parse_args()

    cards = load_cards()
    flip_map = build_flip_lookup(load_flip_map(), cards)
    mse_lookup = build_mse_lookup()
    cards_by_norm = {normalize_name(c["name"]): c for c in cards}

    draftable = draftable_cards(cards, flip_map)
    if not draftable:
        print("No draftable cards found.", file=sys.stderr)
        sys.exit(1)

    custom_cards = [
        build_custom_card(card, mse_lookup, flip_map, cards_by_norm, args.image_base_url)
        for card in draftable
    ]
    sheet_names = [card["name"] for card in draftable]

    output = render_draftmancer(
        custom_cards,
        sheet_names,
        cube_name=args.name,
        boosters_per_player=args.boosters,
    )
    args.output.write_text(output, encoding="utf-8")
    print(f"Wrote {len(draftable)} draftable card(s) to {args.output}")
    print(f"Image base URL: {args.image_base_url}")


if __name__ == "__main__":
    main()
