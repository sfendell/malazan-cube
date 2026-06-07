#!/usr/bin/env python3
# fix_card_filenames: Rename files in a directory to match card names from the MSE set.
# Matches by stripping punctuation (commas, apostrophes, etc.) from both sides, then
# renames to the canonical card name with punctuation restored. Apostrophes in output
# filenames use the straight ASCII apostrophe (') instead of the curly ’ (U+2019).
# Run from repo root: python fix_card_filenames.py [directory] [--dry-run]

import argparse
import re
import sys
from pathlib import Path

from mse_parse import parse_set_blocks, read_set_from_mse

ROOT = Path(__file__).resolve().parent
MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
DEFAULT_DIR = ROOT / "exported_cards"
WIN_BAD_CHARS = r'\/:*?"<>|'
CURLY_APOSTROPHE = "\u2019"  # right single quotation mark (typographic apostrophe)
STRAIGHT_APOSTROPHE = "'"  # ASCII apostrophe (U+0027)


def normalize_name(s: str) -> str:
    """Lowercase, remove non-alphanumeric (commas, apostrophes, punctuation, etc.)."""
    return re.sub(r"[^\w]", "", s).lower()


def parse_stem(stem: str) -> tuple[str, int]:
    """Split 'Food.1' -> ('Food', 1); 'Bugg Humble Manservant' -> (..., 0)."""
    m = re.match(r"^(.+)\.(\d+)$", stem)
    if m:
        return m.group(1), int(m.group(2))
    return stem, 0


def apostrophes_for_filename(name: str) -> str:
    return name.replace(CURLY_APOSTROPHE, STRAIGHT_APOSTROPHE)


def target_stem(card_name: str, dup_index: int) -> str:
    filename = apostrophes_for_filename(card_name)
    if dup_index == 0:
        return filename
    return f"{filename}.{dup_index}"


def filename_unsafe_chars(name: str) -> list[str]:
    return [ch for ch in name if ch in WIN_BAD_CHARS]


def print_rename(old_name: str, new_name: str, *, applied: bool) -> None:
    prefix = "Renamed: " if applied else ""
    msg = f"{prefix}{old_name} -> {new_name}"
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "backslashreplace").decode("ascii"))


def build_name_lookup() -> dict[str, list[str]]:
    """Map normalized card name -> list of canonical names (set-file order)."""
    if not MSE_SET_PATH.exists():
        print(f"MSE set not found: {MSE_SET_PATH}", file=sys.stderr)
        sys.exit(1)

    _, cards_content = read_set_from_mse(MSE_SET_PATH)
    lookup: dict[str, list[str]] = {}
    for card in parse_set_blocks(cards_content):
        name = (card.get("name") or "").strip()
        if not name:
            continue
        lookup.setdefault(normalize_name(name), []).append(name)
    return lookup


def resolve_card_name(stem: str, lookup: dict[str, list[str]]) -> str | None:
    base, dup_index = parse_stem(stem)
    names = lookup.get(normalize_name(base))
    if not names:
        return None
    if dup_index >= len(names):
        return None
    return names[dup_index]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rename files to canonical MSE card names (punctuation restored).",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=DEFAULT_DIR,
        help=f"Directory to scan (default: {DEFAULT_DIR.name}/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print renames without changing files",
    )
    args = parser.parse_args()

    directory = args.directory
    if not directory.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        sys.exit(1)

    lookup = build_name_lookup()
    files = sorted(p for p in directory.iterdir() if p.is_file())

    renamed = 0
    skipped = 0
    unmatched: list[str] = []
    blocked: list[str] = []
    collisions: list[str] = []

    for path in files:
        stem = path.stem
        card_name = resolve_card_name(stem, lookup)
        if card_name is None:
            unmatched.append(path.name)
            continue

        unsafe = filename_unsafe_chars(card_name)
        if unsafe:
            blocked.append(f"{path.name} -> {card_name!r} (illegal chars: {unsafe})")
            continue

        _, dup_index = parse_stem(stem)
        new_stem = target_stem(card_name, dup_index)
        if new_stem == stem:
            skipped += 1
            continue

        new_path = path.with_name(new_stem + path.suffix)
        if new_path.exists() and new_path != path:
            collisions.append(f"{path.name} -> {new_path.name} (target exists)")
            continue

        if args.dry_run:
            print_rename(path.name, new_path.name, applied=False)
        else:
            path.rename(new_path)
            print_rename(path.name, new_path.name, applied=True)
        renamed += 1

    print()
    print(f"Done. Renamed: {renamed}, already correct: {skipped}, unmatched: {len(unmatched)}")
    if blocked:
        print(f"Blocked ({len(blocked)}):")
        for line in blocked:
            print(f"  {line}")
    if collisions:
        print(f"Collisions ({len(collisions)}):")
        for line in collisions:
            print(f"  {line}")
    if unmatched:
        print(f"Unmatched ({len(unmatched)}):")
        for name in unmatched:
            print(f"  {name}")
    if args.dry_run and renamed:
        print("\nRe-run without --dry-run to apply renames.")
    if renamed and not args.dry_run:
        print("Consider running generate_cards_json.py to refresh cards.json img paths.")


if __name__ == "__main__":
    main()
