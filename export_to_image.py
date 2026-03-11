#!/usr/bin/env python3
# export_to_image: Recreate all files in exported_cards/ from the MSE set.
# Runs MSE --export-images; any intermediary files go in __generated__.
# Then regenerates cards.json for the gallery. Run from repo root.

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MSE_EXE = ROOT.parent / "M15-Magic-Pack-main" / "mse.exe"
MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
OUT_DIR = ROOT / "exported_cards"
IMAGE_TEMPLATE = OUT_DIR / "{card.name}.png"
GENERATED = ROOT / "__generated__"


def main():
    if not MSE_EXE.exists():
        print(f"MSE not found at: {MSE_EXE}", file=sys.stderr)
        sys.exit(1)
    if not MSE_SET_PATH.exists():
        print(f"Set file not found: {MSE_SET_PATH}", file=sys.stderr)
        sys.exit(1)

    GENERATED.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for p in OUT_DIR.glob("*.png"):
        p.unlink()

    print("Exporting cards to:", OUT_DIR)
    result = subprocess.run(
        [str(MSE_EXE), "--export-images", str(MSE_SET_PATH), str(IMAGE_TEMPLATE)],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print(f"MSE exited with code {result.returncode}.", file=sys.stderr)
        sys.exit(result.returncode)

    count = len(list(OUT_DIR.glob("*.png")))
    print(f"Exported {count} card(s) to {OUT_DIR}.")

    gen_json = ROOT / "generate_cards_json.py"
    if gen_json.exists():
        subprocess.run([sys.executable, str(gen_json)], cwd=str(ROOT), check=True)
    print("export_to_image done.")


if __name__ == "__main__":
    main()
