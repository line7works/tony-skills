#!/usr/bin/env python3
"""Validate a product box against assets/box-template.md rules.

Usage: validate-box.py <box-file.md>
Exit 0 = VALID. Exit 1 = INVALID (reasons on stdout). Exit 2 = usage error.
"""
import re
import sys


def validate(text):
    errors = []
    headings = re.findall(r"^## (.+)$", text, re.M)
    expected = ["Front", "Back", "Side", "Bottom"]
    if headings != expected:
        errors.append(f"headings must be exactly {expected} in order; found {headings}")
        return errors  # section parsing below relies on the headings

    sections = {}
    parts = re.split(r"^## (Front|Back|Side|Bottom)$", text, flags=re.M)
    # parts[0] is preamble; then alternating name, body
    if parts[0].strip():
        errors.append("no content allowed before '## Front'")
    for name, body in zip(parts[1::2], parts[2::2]):
        sections[name] = body

    front_lines = [l.strip() for l in sections["Front"].splitlines() if l.strip()]
    labels = ["Name:", "Pitch:", "Buyer:"]
    if len(front_lines) != 3 or any(
        not l.startswith(lab) or not l[len(lab):].strip()
        for l, lab in zip(front_lines, labels)
    ):
        errors.append("Front must be exactly 3 non-empty lines: Name:, Pitch:, Buyer:")

    def numbered(body):
        out = []
        for l in body.splitlines():
            m = re.match(r"^\s*(\d+)\.\s*(.*)$", l)
            if m:
                out.append((int(m.group(1)), m.group(2).strip()))
        return out

    for sec, count in (("Back", 3), ("Side", 9), ("Bottom", 3)):
        items = numbered(sections[sec])
        if len(items) != count:
            errors.append(f"{sec} must have exactly {count} numbered items; found {len(items)}")
        nums = [n for n, _ in items]
        if nums != list(range(1, len(nums) + 1)):
            errors.append(f"{sec} items must be numbered 1..{count} in order; found {nums}")
        for n, text in items:
            if not text:
                errors.append(f"{sec} item {n} has no text")
        stray = [l for l in sections[sec].splitlines() if l.strip() and not re.match(r"^\s*\d+\.", l)]
        if stray:
            errors.append(f"{sec} contains non-item lines: {stray[:2]}")

    side_items = [text for _, text in numbered(sections["Side"])]
    tags_seen = []
    for item in side_items:
        m = re.search(r"\[(build|sell|run)\]\s*$", item)
        if not m:
            errors.append(f"Side item lacks a trailing [build]/[sell]/[run] tag: {item!r}")
        else:
            tags_seen.append(m.group(1))
            if not item[: m.start()].strip():
                errors.append(f"Side item has a tag but no property text: {item!r}")
    for tag in ("build", "sell", "run"):
        if side_items and tag not in tags_seen:
            errors.append(f"Side has no item tagged [{tag}]")

    return errors


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    with open(sys.argv[1]) as f:
        errors = validate(f.read())
    if errors:
        print("INVALID")
        for e in errors:
            print(f"- {e}")
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
