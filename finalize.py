#!/usr/bin/env python3
# finalize: Treat the .mse-set file as source of truth and regenerate from it.
# Runs export_to_image, then generate_cards_json (which reads the MSE set directly for meta).

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    os.chdir(ROOT)

    print("=== export_to_image ===")
    r = subprocess.run([sys.executable, str(ROOT / "export_to_image.py")], cwd=str(ROOT))
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("\nfinalize done.")


if __name__ == "__main__":
    main()
