#!/usr/bin/env python3
# import_from_text: Build the .mse-set file from text/ and art/.
# Uses __generated__/mse-extract for unpacking and repacking. Run from repo root.

import re
import shutil
import zipfile
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
MSE_SET_PATH = ROOT / "Malazan Cube of the Fallen.mse-set"
TEXT_DIR = ROOT / "text"
ART_DIR = ROOT / "art"
GENERATED = ROOT / "__generated__"
EXTRACT_DIR = GENERATED / "mse-extract"
SET_PATH = EXTRACT_DIR / "set"

BAD_CHARS = r'\/:*?"<>|'


def get_safe_filename(name: str) -> str:
    for c in BAD_CHARS:
        name = name.replace(c, "_")
    return name.strip()


def type_line_to_mse(super_part: str, sub_part: str) -> tuple:
    """Return (super_type_value, sub_type_value) with MSE markup."""
    super_val = f"<word-list-type-en>{super_part.strip()}</word-list-type-en>" if super_part.strip() else "<word-list-type-en></word-list-type-en>"
    if not sub_part.strip():
        sub_val = ""
    else:
        parts = sub_part.strip().split()
        sub_val = "<atom-sep> </atom-sep>".join(
            f"<word-list-class-en>{p}</word-list-class-en>" for p in parts
        ) + "<soft><atom-sep> </atom-sep></soft><word-list-class-en></word-list-class-en>"
    return super_val, sub_val


def escape_mse(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse_text_file(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    lines = content.replace("\r", "").rstrip().split("\n")
    name = lines[0].strip() if lines else ""
    cost = ""
    type_line = ""
    pt_line = ""
    power, toughness = "", ""
    rules = []
    flavor = []
    past_header = False
    blank = False
    for i in range(1, len(lines)):
        line = lines[i]
        t = line.strip()
        m = re.match(r"^Cost:\s*(.*)$", line)
        if m:
            cost = m.group(1).strip()
            continue
        m = re.match(r"^Type:\s*(.*)$", line)
        if m:
            type_line = m.group(1).strip()
            continue
        m = re.match(r"^P/T:\s*(.*)$", line)
        if m:
            pt_line = m.group(1).strip()
            continue
        if re.match(r"^\s*$", line):
            blank = True
            continue
        if blank and not past_header:
            past_header = True
        if not past_header:
            continue
        if blank and rules:
            flavor.append(t)
        else:
            rules.append(t)
    # Type line: "Legendary Creature - Elder Orc Giant" -> super "Legendary Creature", sub "Elder Orc Giant"
    if " - " in type_line:
        super_part, sub_part = type_line.split(" - ", 1)
    else:
        super_part, sub_part = type_line, ""
    if pt_line and "/" in pt_line:
        a, b = pt_line.split("/", 1)
        power, toughness = a.strip(), b.strip()
    return {
        "name": name,
        "cost": cost,
        "super_part": super_part.strip(),
        "sub_part": sub_part.strip(),
        "power": power,
        "toughness": toughness,
        "rules": "\n".join(rules),
        "flavor": " ".join(flavor),
    }


def build_card_block(template: dict, card: dict, image_file: str) -> str:
    super_type, sub_type = type_line_to_mse(card["super_part"], card["sub_part"])
    rule_lines = card["rules"].split("\n") if card["rules"] else []
    rule_text_val = "\n\t\t".join(rule_lines) if rule_lines else ""
    flavor_esc = escape_mse(card["flavor"])
    flavor_val = f"<i-flavor>{flavor_esc}</i-flavor>" if flavor_esc else "<i-flavor></i-flavor>"

    block = template.copy()
    block["name"] = card["name"]
    block["casting_cost"] = card["cost"]
    block["image"] = image_file
    block["super_type"] = super_type
    block["sub_type"] = sub_type
    block["rule_text"] = rule_text_val
    block["flavor_text"] = flavor_val
    block["power"] = card["power"]
    block["toughness"] = card["toughness"]
    block["time_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    for key in ["has_styling", "notes", "time_created", "time_modified", "name", "casting_cost", "image",
                "image_2", "mainframe_image", "mainframe_image_2", "super_type", "super_type_2", "super_type_3", "super_type_4",
                "sub_type", "sub_type_2", "sub_type_3", "sub_type_4", "rule_text", "flavor_text", "power", "toughness",
                "card_code_text", "card_code_text_2", "card_code_text_3"]:
        val = block.get(key, "")
        if key == "rule_text" and val:
            lines.append(f"\trule_text:")
            for ln in val.split("\n"):
                lines.append(f"\t\t{ln}")
        else:
            lines.append(f"\t{key}: {val}")
    return "\n".join(lines)  # block content only (no leading "card:\n")


def parse_set_template(set_content: str) -> tuple:
    """Return (header, template_dict). Template is first card block as dict."""
    first = set_content.find("card:\n")
    if first < 0:
        return set_content, {}
    header = set_content[:first]  # everything before first "card:\n"
    blocks = re.split(r"(?m)^card:\r?\n", set_content[first:])
    if len(blocks) < 2:
        return set_content, {}
    block = blocks[1]
    lines = re.split(r"\r?\n", block)
    template = {}
    key = None
    value_parts = []
    for line in lines:
        m = re.match(r"^\t([a-z_0-9]+):\s*(.*)$", line)
        if m:
            if key:
                template[key] = "\n".join(value_parts).strip() if value_parts else ""
            key = m.group(1)
            value_parts = [m.group(2)] if m.group(2).strip() else []
        elif key and re.match(r"^\t\t", line):
            value_parts.append(line.strip())
        else:
            m2 = re.match(r"^\t([a-z_0-9]+):\s*$", line)
            if m2:
                if key:
                    template[key] = "\n".join(value_parts).strip() if value_parts else ""
                key = m2.group(1)
                value_parts = []
    if key:
        template[key] = "\n".join(value_parts).strip() if value_parts else ""
    # Defaults for optional fields
    for k in ["has_styling", "notes", "time_created", "time_modified", "image_2", "mainframe_image", "mainframe_image_2",
              "super_type_2", "super_type_3", "super_type_4", "sub_type_2", "sub_type_3", "sub_type_4",
              "card_code_text", "card_code_text_2", "card_code_text_3"]:
        template.setdefault(k, "")
    template.setdefault("time_created", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return header, template


def main():
    if not TEXT_DIR.exists():
        print(f"Text directory not found: {TEXT_DIR}", file=sys.stderr)
        sys.exit(1)
    if not MSE_SET_PATH.exists():
        print(f"Existing set file required for template: {MSE_SET_PATH}", file=sys.stderr)
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
        print(f"Set file not in extract: {SET_PATH}", file=sys.stderr)
        sys.exit(1)

    set_content = SET_PATH.read_text(encoding="utf-8")
    header, template = parse_set_template(set_content)
    if not template:
        print("Could not parse a card template from set file.", file=sys.stderr)
        sys.exit(1)

    # Remove old card images so we replace with art/
    for p in EXTRACT_DIR.glob("image*.png"):
        p.unlink()

    text_files = sorted(TEXT_DIR.glob("*.txt"))
    cards = []
    for f in text_files:
        data = parse_text_file(f)
        if not data["name"]:
            continue
        cards.append(data)

    for i, card in enumerate(cards, 1):
        image_name = f"image{i}.png"
        safe = get_safe_filename(card["name"])
        art_src = ART_DIR / f"{safe}.png"
        if art_src.exists():
            shutil.copy2(art_src, EXTRACT_DIR / image_name)
        # else: leave no image (MSE may show blank)

    new_blocks = []
    for i, card in enumerate(cards, 1):
        block = build_card_block(template, card, f"image{i}.png")
        new_blocks.append(block)

    new_set_content = header + "card:\n" + ("\ncard:\n".join(new_blocks)) + "\n"
    SET_PATH.write_text(new_set_content, encoding="utf-8")

    out_zip = GENERATED / "Malazan Cube of the Fallen.mse-set"
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in EXTRACT_DIR.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(EXTRACT_DIR))
    if MSE_SET_PATH.exists():
        MSE_SET_PATH.unlink()
    shutil.copy2(out_zip, MSE_SET_PATH)
    print(f"Wrote {MSE_SET_PATH} from {len(cards)} cards (text + art).")


if __name__ == "__main__":
    main()
