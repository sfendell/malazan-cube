#!/usr/bin/env python3
# mtg_clippy: LLM-powered grammar/wording checker for MTG cards.
# ONLY modifies files in text/ (ability text only; name, cost, type, P/T unchanged).
# Writes list of changed card names to __generated__/clippy-changed.txt.
# Requires: OPENAI_API_KEY. Run from repo root.

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXT_DIR = ROOT / "text"
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

You will receive only the ability text (rules and optional flavor). Return ONLY the fixed ability text—nothing else. No card name, no Cost/Type/P/T lines, no explanation, no markdown."""


def get_header_and_ability(content: str) -> dict:
    lines = content.replace("\r", "").split("\n")
    header_end = -1
    blank_after_header = False
    for i, line in enumerate(lines):
        if re.match(r"^(Cost|Type|P/T):", line):
            continue
        if re.match(r"^\s*$", line):
            blank_after_header = True
            continue
        if blank_after_header:
            header_end = i
            break
    if header_end < 0:
        header_end = len(lines)
    header_lines = lines[:header_end]
    ability_lines = lines[header_end:]
    return {
        "HeaderLines": header_lines,
        "AbilityText": "\n".join(ability_lines).strip(),
    }


def get_full_card_content(header_lines: list, ability_text: str) -> str:
    out = [ln.rstrip() for ln in header_lines]
    for ln in ability_text.split("\n"):
        out.append(ln.rstrip())
    return "\n".join(out).rstrip()


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


def main():
    if not TEXT_DIR.exists():
        print(f"Text directory not found: {TEXT_DIR}", file=sys.stderr)
        sys.exit(1)

    files = sorted(TEXT_DIR.glob("*.txt"))
    total = len(files)
    changed = []

    for n, f in enumerate(files, 1):
        content = f.read_text(encoding="utf-8")
        content = content.replace("\r\n", "\n").rstrip()
        if not content:
            continue
        parsed = get_header_and_ability(content)
        ability_only = parsed["AbilityText"]
        if not ability_only:
            print(f"[{n}/{total}] {f.name} (no ability text, skip)")
            continue
        print(f"[{n}/{total}] {f.name}...")
        fixed_ability = get_clippy_from_llm(ability_only)
        if not fixed_ability:
            continue
        new_content = get_full_card_content(parsed["HeaderLines"], fixed_ability)
        orig_norm = content.replace("\r\n", "\n").rstrip()
        if new_content != orig_norm:
            f.write_text(new_content + "\n", encoding="utf-8")
            name = content.split("\n")[0].strip()
            changed.append(name)
        time.sleep(0.3)

    GENERATED.mkdir(parents=True, exist_ok=True)
    CHANGED_LIST_PATH.write_text("\n".join(changed), encoding="utf-8")
    print(f"mtg_clippy: Processed {total} cards. Changed: {len(changed)}. List: {CHANGED_LIST_PATH}")


if __name__ == "__main__":
    main()
