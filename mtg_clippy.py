#!/usr/bin/env python3
# mtg_clippy: LLM-powered grammar/wording checker for MTG card text.
# Operates on the .mse-set file: extract, parse set, fix rule_text and flavor_text per card, write back, repack.
# Writes changed-card list to __generated__/clippy-changed.txt.
# Requires: OPENAI_API_KEY. Run from repo root.
#
# Usage: python mtg_clippy.py [--cards 1 5 10]   # only those collector numbers (1-based, alphabetical by name)
#        python mtg_clippy.py --list             # print collector # and name for each card, then exit

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from mse_parse import (
    EXTRACT_DIR,
    ROOT,
    extract_mse_set,
    read_set_content,
    write_set_content,
    parse_set_blocks,
    serialize_cards_content,
    strip_mse_markup,
    repack_mse_set,
)

MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
GENERATED = ROOT / "__generated__"
CHANGED_LIST_PATH = GENERATED / "clippy-changed.txt"

SYSTEM_PROMPT = """You fix only the wording of Magic the Gathering card ability text (rules and flavor). Do not change card name, cost, type, or P/T.

Rules:
- Fix wording to standard Magic the Gathering card syntax.
- "Slow" is a valid keyword for activated abilities (use it as-is).
- Ignore incorrect usage of the mechanic "ascends" if it appears.
- Use "cook" instead of "create a food token".
- Use "bleed" instead of "create a blood token".
- Treat Malazan, Pure, Child, and Alien as valid MTG types.

You will receive only the ability text (rules and optional flavor). Return ONLY the fixed ability text—nothing else. No card name, no Cost/Type/P/T lines, no explanation, no markdown. If there is flavor text, put it after a blank line."""


def get_clippy_from_llm(ability_text: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": ability_text},
        ],
        "temperature": 0.2,
    })
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body.encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"LLM request failed: {e}", file=sys.stderr)
        raise


def split_rules_and_flavor(fixed: str) -> tuple:
    """If fixed has a blank line, last paragraph is flavor; else all rules."""
    if "\n\n" in fixed:
        parts = fixed.split("\n\n")
        rule_text = "\n".join(parts[:-1]).strip()
        flavor_text = parts[-1].strip()
        return rule_text, flavor_text
    return fixed.strip(), ""


def _normalize_for_compare(s: str) -> str:
    """Normalize so whitespace-only differences are ignored when deciding if content changed."""
    return "\n".join(line.strip() for line in s.splitlines()).strip()


def main():
    parser = argparse.ArgumentParser(description="Fix MTG card wording via LLM. Optionally limit to specific card numbers (1-based).")
    parser.add_argument(
        "--cards", "-c",
        type=int,
        nargs="*",
        metavar="N",
        help="Only process these collector numbers (1-based, alphabetical by card name). Omit to process all.",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Print collector number and name for each card (alphabetical), then exit.",
    )
    args = parser.parse_args()
    collector_numbers_requested = set(args.cards) if args.cards else None  # None = all

    if not MSE_SET_PATH.exists():
        print(f"MSE set not found: {MSE_SET_PATH}", file=sys.stderr)
        sys.exit(1)

    GENERATED.mkdir(parents=True, exist_ok=True)
    extract_mse_set(MSE_SET_PATH, EXTRACT_DIR)
    header, cards_content = read_set_content(EXTRACT_DIR)
    cards = list(parse_set_blocks(cards_content))
    total = len(cards)
    # Collector number = 1-based rank when sorted by card name (alphabetical)
    sorted_by_name = sorted(enumerate(cards), key=lambda x: (x[1].get("name") or "").strip().lower())
    index_to_collector = {idx: cn for cn, (idx, _) in enumerate(sorted_by_name, 1)}
    if args.list:
        for cn, (idx, card) in enumerate(sorted_by_name, 1):
            name = (card.get("name") or "").strip()
            print(f"{cn}\t{name}")
        return
    changed = []
    processed_count = 0
    reports = []  # list of (name, rule_before, rule_after or None, error_msg or None)

    for idx, card in enumerate(cards):
        collector_num = index_to_collector.get(idx, idx + 1)
        if collector_numbers_requested is not None and collector_num not in collector_numbers_requested:
            continue
        name = (card.get("name") or "").strip()
        rule_text = strip_mse_markup(card.get("rule_text", ""), preserve_newlines=True).strip()
        flavor_text = strip_mse_markup(card.get("flavor_text", "")).strip()
        ability = rule_text + ("\n\n" + flavor_text if flavor_text else "")
        if not ability:
            print(f"[{collector_num}/{total}] {name or '?'} (no ability text, skip)")
            continue
        processed_count += 1
        print(f"[{collector_num}/{total}] {name} (collector #{collector_num})...")
        fixed = get_clippy_from_llm(ability)
        if not fixed:
            reports.append((name, rule_text, None, f"Error: LLM returned no text for card {name}."))
            continue
        new_rule, new_flavor = split_rules_and_flavor(fixed)
        # Only count as changed if content actually differs (ignore whitespace-only)
        if _normalize_for_compare(new_rule) != _normalize_for_compare(rule_text) or _normalize_for_compare(new_flavor) != _normalize_for_compare(flavor_text):
            card["rule_text"] = new_rule
            card["flavor_text"] = new_flavor
            changed.append(name)
            reports.append((name, rule_text, new_rule, None))
        else:
            reports.append((name, rule_text, None, None))
        time.sleep(0.3)

    if changed:
        write_set_content(EXTRACT_DIR, header, serialize_cards_content(cards))
        repack_mse_set(EXTRACT_DIR, MSE_SET_PATH)
    CHANGED_LIST_PATH.write_text("\n".join(changed), encoding="utf-8")
    print(f"mtg_clippy: Processed {processed_count} card(s). Changed: {len(changed)}. List: {CHANGED_LIST_PATH}")

    # Show before/after, "no edits", or error for each processed card
    print()
    for name, rule_before, rule_after, error_msg in reports:
        if error_msg is not None:
            print(error_msg)
        elif rule_after is not None:
            print(f"Card {name}:")
            print("Rules text before clippy:")
            print(rule_before)
            print("=======")
            print("Rules text after clippy:")
            print(rule_after)
        else:
            print(f"No edits made for card {name}.")
        print()


if __name__ == "__main__":
    main()
