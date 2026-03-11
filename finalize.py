#!/usr/bin/env python3
# finalize: Treat the .mse-set file as source of truth and regenerate from it.
# Runs export_to_text, export_to_image, generate_cards_json.
# Does NOT copy exported_cards -> art/: art/ is for source illustrations only; exported_cards are full card renders.

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    os.chdir(ROOT)

    # 1. MSE -> text/
    print("=== export_to_text ===")
    r = subprocess.run([sys.executable, str(ROOT / "export_to_text.py")], cwd=str(ROOT))
    if r.returncode != 0:
        sys.exit(r.returncode)

    # 2. MSE -> exported_cards/ and cards.json
    print("\n=== export_to_image ===")
    r = subprocess.run([sys.executable, str(ROOT / "export_to_image.py")], cwd=str(ROOT))
    if r.returncode != 0:
        sys.exit(r.returncode)

    print("\nfinalize done.")


if __name__ == "__main__":
    main()
