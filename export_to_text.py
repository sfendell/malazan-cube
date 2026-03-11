#!/usr/bin/env python3
# export_to_text: Recreate all files in text/ from the MSE set.
# Each file is a single JSON blob with name, cost, types, subtypes, supertypes, power, toughness, artist, rule_text, flavor_text.
# Extracts the .mse-set to __generated__, parses the set file, overwrites text/*.txt.
# Run from repo root.

import json
import re
import zipfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
TEXT_DIR = ROOT / "text"
GENERATED = ROOT / "__generated__"
EXTRACT_DIR = GENERATED / "mse-extract"
SET_PATH = EXTRACT_DIR / "set"

BAD_CHARS = r'\/:*?"<>|'
# MTG supertypes (rest of type line before " - " is types)
SUPERTYPES = {"Legendary", "Snow", "Basic", "World"}


def get_safe_filename(name: str) -> str:
    for c in BAD_CHARS:
        name = name.replace(c, "_")
    return name.strip()


def strip_mse_markup(s: str, preserve_newlines: bool = False) -> str:
    if not s:
        return s
    s = re.sub(r"<sym-auto>([^<]*)</sym-auto>", r"\1", s)
    s = re.sub(r"<key>([^<]*)</key>", r"\1", s)
    s = re.sub(r"<param-name>([^<]*)</param-name>", r"\1", s)
    s = re.sub(r"<param-cost>([^<]*)</param-cost>", r"\1", s)
    s = re.sub(r"<i-flavor>([^<]*)</i-flavor>", r"\1", s)
    s = re.sub(r"<bullet>[^<]*</bullet>", "", s)
    s = re.sub(r"</?li>", "", s)
    s = re.sub(r"<margin:[^>]*>", "", s)
    s = re.sub(r"<error-spelling:[^>]*>([^<]*)</error-spelling[^>]*>", r"\1", s)
    s = re.sub(r"<nospellcheck>[^<]*</nospellcheck>", "", s)
    s = re.sub(r"<kw-[^>]*>", "", s)
    s = re.sub(r"</kw-[^>]*>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    if preserve_newlines:
        lines = [" ".join(ln.split()).strip() for ln in s.split("\n")]
        return "\n".join(ln for ln in lines if ln).strip()
    return " ".join(s.split()).strip()


def strip_type_markup(s: str) -> str:
    if not s:
        return s
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return " ".join(s.split()).strip()


def parse_type_line(super_type: str, sub_type: str) -> tuple:
    """Return (supertypes, types, subtypes). super_type e.g. 'Legendary Creature', sub_type e.g. 'Elder Elf'."""
    super_tokens = super_type.strip().split() if super_type else []
    supertypes = []
    types = []
    for t in super_tokens:
        if t in SUPERTYPES:
            supertypes.append(t)
        else:
            types.append(t)
    subtypes = sub_type.strip().split() if sub_type else []
    return supertypes, types, subtypes


def parse_set_blocks(content: str):
    blocks = re.split(r"(?m)^card:\r?\n", content)
    for block in blocks:
        if not block.strip():
            continue
        lines = re.split(r"\r?\n", block)
        card = {}
        key = None
        value_parts = []
        for line in lines:
            m = re.match(r"^\t([a-z_0-9]+):\s*(.*)$", line)
            if m:
                if key:
                    card[key] = "\n".join(value_parts).strip() if value_parts else ""
                key = m.group(1)
                value_parts = [m.group(2)] if m.group(2).strip() else []
            elif key and re.match(r"^\t\t", line):
                value_parts.append(line.strip())
            else:
                m2 = re.match(r"^\t([a-z_0-9]+):\s*$", line)
                if m2:
                    if key:
                        card[key] = "\n".join(value_parts).strip() if value_parts else ""
                    key = m2.group(1)
                    value_parts = []
        if key:
            card[key] = "\n".join(value_parts).strip() if value_parts else ""
        yield card


def main():
    if not MSE_SET_PATH.exists():
        print(f"Set file not found: {MSE_SET_PATH}", file=sys.stderr)
        sys.exit(1)

    GENERATED.mkdir(parents=True, exist_ok=True)
    if EXTRACT_DIR.exists():
        for p in EXTRACT_DIR.rglob("*"):
            if p.is_file():
                p.unlink()
        for p in sorted(EXTRACT_DIR.rglob("*"), key=lambda x: -len(x.parts)):
            if p.is_dir():
                p.rmdir()
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(MSE_SET_PATH, "r") as zf:
        zf.extractall(EXTRACT_DIR)
    print(f"Extracted MSE set to {EXTRACT_DIR}")

    if not SET_PATH.exists():
        print(f"Set file not found in extract: {SET_PATH}", file=sys.stderr)
        sys.exit(1)

    set_content = SET_PATH.read_text(encoding="utf-8")
    first_card = set_content.find("\ncard:\n")
    if first_card >= 0:
        set_content = set_content[first_card:]

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    for f in TEXT_DIR.glob("*.txt"):
        f.unlink()

    count = 0
    for card in parse_set_blocks(set_content):
        name = card.get("name")
        if not name:
            continue
        name = name.strip()
        cost = card.get("casting_cost", "").strip()
        super_type = strip_type_markup(card.get("super_type", ""))
        sub_type = strip_type_markup(card.get("sub_type", ""))
        supertypes, types, subtypes = parse_type_line(super_type, sub_type)
        power = card.get("power", "").strip()
        toughness = card.get("toughness", "").strip()
        artist = card.get("illustrator", "").strip()
        rule_text = strip_mse_markup(card.get("rule_text", ""), preserve_newlines=True)
        flavor_text = strip_mse_markup(card.get("flavor_text", ""))

        blob = {
            "name": name,
            "cost": cost,
            "types": types,
            "subtypes": subtypes,
            "supertypes": supertypes,
            "power": power,
            "toughness": toughness,
            "artist": artist,
            "rule_text": rule_text,
            "flavor_text": flavor_text,
        }
        safe_name = get_safe_filename(name)
        txt_path = TEXT_DIR / f"{safe_name}.txt"
        txt_path.write_text(json.dumps(blob, indent=2, ensure_ascii=False), encoding="utf-8")
        count += 1

    print(f"Wrote {count} card(s) to {TEXT_DIR}")

    # Keep cards.json in sync for the gallery (uses text/ + exported_cards/)
    gen_json = ROOT / "generate_cards_json.py"
    if gen_json.exists():
        import subprocess
        subprocess.run([sys.executable, str(gen_json)], cwd=str(ROOT), check=True)


if __name__ == "__main__":
    main()
