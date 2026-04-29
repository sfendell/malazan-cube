#!/usr/bin/env python3
# export_to_image: Write PNGs under exported_cards/ from the MSE set.
# Default: full set (clears exported_cards/*.png first, then MSE on the full .mse-set).
# With --cards N ...: only those collector numbers (1-based, alphabetical by name, same as
# mtg_clippy / finalize). Builds a temporary subset .mse-set so MSE only renders those cards;
# other PNGs in exported_cards/ are left unchanged. Then regenerates cards.json.

import argparse
import subprocess
import sys
from pathlib import Path

from mse_parse import (
    cards_for_collector_subset,
    extract_mse_set,
    parse_set_blocks,
    read_set_content,
    repack_mse_set,
    serialize_cards_content,
    write_set_content,
)

ROOT = Path(__file__).resolve().parent
MSE_EXE = ROOT.parent / "M15-Magic-Pack-main" / "mse.exe"
MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
OUT_DIR = ROOT / "exported_cards"
IMAGE_TEMPLATE = OUT_DIR / "{card.name}.png"
GENERATED = ROOT / "__generated__"
SUBSET_EXTRACT = GENERATED / "export_subset_work"
SUBSET_SET_PATH = GENERATED / "_subset_export.mse-set"


def main():
    parser = argparse.ArgumentParser(
        description="Export card images from the Malazan cube MSE set.",
    )
    parser.add_argument(
        "--cards", "-c",
        type=int,
        nargs="*",
        metavar="N",
        help="Only export these collector numbers (1-based, A–Z by name). Omit for a full export.",
    )
    args = parser.parse_args()
    collectors = set(args.cards) if args.cards else None

    if not MSE_EXE.exists():
        print(f"MSE not found at: {MSE_EXE}", file=sys.stderr)
        sys.exit(1)
    if not MSE_SET_PATH.exists():
        print(f"Set file not found: {MSE_SET_PATH}", file=sys.stderr)
        sys.exit(1)

    GENERATED.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if collectors:
        extract_mse_set(MSE_SET_PATH, SUBSET_EXTRACT)
        header, cards_content = read_set_content(SUBSET_EXTRACT)
        cards = list(parse_set_blocks(cards_content))
        subset = cards_for_collector_subset(cards, collectors)
        if not subset:
            print(
                f"No cards matched collector numbers {sorted(collectors)}.",
                file=sys.stderr,
            )
            sys.exit(1)
        write_set_content(SUBSET_EXTRACT, header, serialize_cards_content(subset))
        repack_mse_set(SUBSET_EXTRACT, SUBSET_SET_PATH)
        set_for_mse = SUBSET_SET_PATH
        print(
            f"Exporting {len(subset)} card image(s) (collectors {sorted(collectors)}) to:",
            OUT_DIR,
        )
    else:
        for p in OUT_DIR.glob("*.png"):
            p.unlink()
        set_for_mse = MSE_SET_PATH
        print("Exporting full set to:", OUT_DIR)

    result = subprocess.run(
        [str(MSE_EXE), "--export-images", str(set_for_mse), str(IMAGE_TEMPLATE)],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print(f"MSE exited with code {result.returncode}.", file=sys.stderr)
        sys.exit(result.returncode)

    if collectors:
        print(f"MSE wrote {len(subset)} new/updated PNG(s) under {OUT_DIR}.")
    else:
        count = len(list(OUT_DIR.glob("*.png")))
        print(f"Exported {count} card(s) to {OUT_DIR}.")

    gen_json = ROOT / "generate_cards_json.py"
    if gen_json.exists():
        subprocess.run([sys.executable, str(gen_json)], cwd=str(ROOT), check=True)
    print("export_to_image done.")


if __name__ == "__main__":
    main()
