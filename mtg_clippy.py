#!/usr/bin/env python3
# mtg_clippy: LLM-powered grammar/wording checker for MTG cards.
# ONLY modifies files in text/ (rule_text and flavor_text only; other fields unchanged).
# Reads/writes each .txt as a JSON blob. Writes changed-card list to __generated__/clippy-changed.txt.
# Requires: OPENAI_API_KEY. Run from repo root.

import json
import os
import sys
import time
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

You will receive only the ability text (rules and optional flavor). Return ONLY the fixed ability text—nothing else. No card name, no Cost/Type/P/T lines, no explanation, no markdown. If there is flavor text, put it after a blank line."""


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


def split_rules_and_flavor(fixed: str) -> tuple:
    """If fixed has a blank line, last paragraph is flavor; else all rules."""
    if "\n\n" in fixed:
        parts = fixed.split("\n\n")
        rule_text = "\n".join(parts[:-1]).strip()
        flavor_text = parts[-1].strip()
        return rule_text, flavor_text
    return fixed.strip(), ""


def main():
    if not TEXT_DIR.exists():
        print(f"Text directory not found: {TEXT_DIR}", file=sys.stderr)
        sys.exit(1)

    GENERATED.mkdir(parents=True, exist_ok=True)
    files = sorted(TEXT_DIR.glob("*.txt"))
    total = len(files)
    changed = []

    for n, f in enumerate(files, 1):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        rule_text = (data.get("rule_text") or "").strip()
        flavor_text = (data.get("flavor_text") or "").strip()
        ability = rule_text + ("\n\n" + flavor_text if flavor_text else "")
        if not ability:
            print(f"[{n}/{total}] {f.name} (no ability text, skip)")
            continue
        print(f"[{n}/{total}] {f.name}...")
        fixed = get_clippy_from_llm(ability)
        if not fixed:
            continue
        new_rule, new_flavor = split_rules_and_flavor(fixed)
        if new_rule != rule_text or new_flavor != flavor_text:
            data["rule_text"] = new_rule
            data["flavor_text"] = new_flavor
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            changed.append((data.get("name") or f.stem).strip())
        time.sleep(0.3)

    CHANGED_LIST_PATH.write_text("\n".join(changed), encoding="utf-8")
    print(f"mtg_clippy: Processed {total} cards. Changed: {len(changed)}. List: {CHANGED_LIST_PATH}")


if __name__ == "__main__":
    main()
