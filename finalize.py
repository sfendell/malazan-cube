#!/usr/bin/env python3
# finalize: Regenerate exported_cards and cards.json from the .mse-set file.
# With no args: export all card images (full MSE run).
# With --cards 1 5 10: export only those collector numbers (1-based, A–Z by name); fast path
# for a few edited cards. Used by mtg_clippy after it edits specific cards.

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
GENERATED = ROOT / "__generated__"


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
        GENERATED.mkdir(parents=True, exist_ok=True)
        print(
            f"Finalize: exporting images only for collector numbers "
            f"{sorted(export_only_collectors)} ({len(export_only_collectors)} card(s)).",
        )

    print("\n=== export_to_image ===")
    cmd = [sys.executable, str(ROOT / "export_to_image.py")]
    if export_only_collectors is not None:
        cmd += ["--cards"] + [str(n) for n in sorted(export_only_collectors)]
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        sys.exit(r.returncode)

    print("\nfinalize done.")


if __name__ == "__main__":
    main()
