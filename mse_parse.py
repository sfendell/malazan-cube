#!/usr/bin/env python3
# mse_parse: Shared MSE set parsing/serialization. Extract zip, parse set file, strip markup, serialize back.
# Used by generate_cards_json and mtg_clippy. Run from repo root.

import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERATED = ROOT / "__generated__"
EXTRACT_DIR = GENERATED / "mse-extract"
SET_FILENAME = "set"

SUPERTYPES = {"Legendary", "Snow", "Basic", "World"}
CARD_KEYS_ORDER = [
    "has_styling", "notes", "time_created", "time_modified", "name", "casting_cost", "image",
    "image_2", "mainframe_image", "mainframe_image_2", "super_type", "super_type_2", "super_type_3", "super_type_4",
    "sub_type", "sub_type_2", "sub_type_3", "sub_type_4", "rule_text", "flavor_text", "power", "toughness",
    "illustrator", "card_code_text", "card_code_text_2", "card_code_text_3",
]
def extract_mse_set(mse_path: Path, extract_dir: Path) -> None:
    """Extract .mse-set zip to extract_dir. Clears extract_dir first."""
    if extract_dir.exists():
        for p in extract_dir.rglob("*"):
            if p.is_file():
                p.unlink()
        for p in sorted(extract_dir.rglob("*"), key=lambda x: -len(x.parts)):
            if p.is_dir():
                p.rmdir()
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(mse_path, "r") as zf:
        zf.extractall(extract_dir)


def read_set_content(extract_dir: Path) -> tuple[str, str]:
    """Read set file from extract_dir. Returns (header, cards_content). cards_content starts at first 'card:\\n'."""
    set_path = extract_dir / SET_FILENAME
    content = set_path.read_text(encoding="utf-8")
    first = content.find("\ncard:\n")
    if first >= 0:
        return content[: first + 1], content[first + 1 :]
    return content, ""


def write_set_content(extract_dir: Path, header: str, cards_content: str) -> None:
    """Write set file back to extract_dir."""
    (extract_dir / SET_FILENAME).write_text(header + cards_content, encoding="utf-8")


def parse_set_blocks(content: str):
    """Yield card dicts from cards_content (the part after header)."""
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
                    val = "\n".join(value_parts) if value_parts else ""
                    if val.startswith("\n"):
                        val = val[1:]
                    card[key] = val
                key = m.group(1)
                value_parts = [m.group(2)]
            elif key and re.match(r"^\t\t", line):
                value_parts.append(line[2:].rstrip("\r"))
            else:
                m2 = re.match(r"^\t([a-z_0-9]+):\s*$", line)
                if m2:
                    if key:
                        val = "\n".join(value_parts) if value_parts else ""
                        if val.startswith("\n"):
                            val = val[1:]
                        card[key] = val
                    key = m2.group(1)
                    value_parts = []
        if key:
            val = "\n".join(value_parts) if value_parts else ""
            if val.startswith("\n"):
                val = val[1:]
            card[key] = val
        yield card


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
    s = re.sub(r"<nospellcheck>([^<]*)</nospellcheck>", r"\1", s)
    s = re.sub(r"<kw-[^>]*>", "", s)
    s = re.sub(r"</kw-[^>]*>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    if preserve_newlines:
        return s
    return " ".join(s.split()).strip()


def strip_type_markup(s: str) -> str:
    if not s:
        return s
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return " ".join(s.split()).strip()


def parse_type_line(super_type: str, sub_type: str) -> tuple:
    """Return (supertypes, types, subtypes)."""
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


def type_line_display(super_type: str, sub_type: str) -> str:
    """Build display type line from parsed super/sub (after strip_type_markup)."""
    supertypes, types, subtypes = parse_type_line(super_type, sub_type)
    first = " ".join(supertypes + types)
    second = " ".join(subtypes)
    if not second:
        return first
    return f"{first} - {second}"


def serialize_card_block(card: dict) -> str:
    """Serialize one card dict to set file block (no leading 'card:\\n')."""
    keys_order = [k for k in CARD_KEYS_ORDER if k in card]
    keys_order += sorted(k for k in card if k not in CARD_KEYS_ORDER)
    lines = []
    for key in keys_order:
        val = card.get(key, "")
        if key == "rule_text" and val:
            lines.append("\trule_text:")
            for ln in val.split("\n"):
                lines.append(f"\t\t{ln}")
        else:
            lines.append(f"\t{key}: {val}")
    return "\n".join(lines)


def serialize_cards_content(cards: list[dict]) -> str:
    """Turn list of card dicts into the cards part of the set file (no header)."""
    blocks = [serialize_card_block(c) for c in cards]
    return "card:\n" + "\ncard:\n".join(blocks) + "\n"


def repack_mse_set(extract_dir: Path, mse_path: Path) -> None:
    """Zip extract_dir contents into .mse-set at mse_path. Overwrites mse_path."""
    if mse_path.exists():
        mse_path.unlink()
    with zipfile.ZipFile(mse_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in extract_dir.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(extract_dir))
