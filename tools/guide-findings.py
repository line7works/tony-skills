#!/usr/bin/env python3
"""Compile guide findings for the skills v2 rebuild.

Reads the capture log (docs/guide-findings.md) plus any `GUIDE:` lines that /fb
dropped into a docs/feedback.md under ~/Developer, and prints a compile report:
counts, then every finding grouped by verdict (contradicts, adds, held) and step,
then the Verified-column candidates (held findings with harness and date).

Usage:
  python3 tools/guide-findings.py            # markdown report to stdout
  python3 tools/guide-findings.py --check    # validate every line; exit 1 on a malformed one
  python3 tools/guide-findings.py --since 2026-10-01
  python3 tools/guide-findings.py --json

No dependencies beyond the standard library. Never edits any file.
"""
import argparse, glob, json, os, re, sys

HOME = os.path.expanduser("~")
LOG = os.path.join(HOME, "Developer", "tony-skills", "docs", "guide-findings.md")
FEEDBACK_GLOBS = [
    os.path.join(HOME, "Developer", "*", "docs", "feedback.md"),
    os.path.join(HOME, "Developer", "tony-skills-*", "docs", "feedback.md"),
]
VERDICTS = ("contradicts", "adds", "held")
SEP = " · "
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STEP = re.compile(r"\bE(\d{1,2})\b")


def parse_log_line(line, source, lineno):
    """A log line: - date · E<n> · harness · verdict · "note" · evidence(optional)."""
    body = line[2:].strip()
    parts = [p.strip() for p in body.split(SEP)]
    if len(parts) < 5:
        return None, f"{source}:{lineno}: expected at least 5 fields separated by ' · ', got {len(parts)}"
    date, step, harness, verdict = parts[0], parts[1], parts[2], parts[3].lower()
    note = parts[4]
    evidence = SEP.join(parts[5:]) if len(parts) > 5 else ""
    if not DATE.match(date):
        return None, f"{source}:{lineno}: bad date {date!r}"
    if not STEP.search(step):
        return None, f"{source}:{lineno}: step field must contain E<n>, got {step!r}"
    if verdict not in VERDICTS:
        return None, f"{source}:{lineno}: verdict must be one of {VERDICTS}, got {verdict!r}"
    if not (note.startswith('"') and note.endswith('"') and len(note) > 2):
        return None, f"{source}:{lineno}: the note must be a quoted string"
    return {
        "date": date, "step": "E" + STEP.search(step).group(1), "harness": harness,
        "verdict": verdict, "note": note[1:-1], "evidence": evidence,
        "source": f"{source}:{lineno}", "origin": "log",
    }, None


def parse_fb_line(line, source, lineno):
    """An /fb inbox line whose note starts with GUIDE:. Verdict and step are read from the note."""
    m = re.match(r"^- (\d{4}-\d{2}-\d{2}) · (.*?) · (.*?) · \"GUIDE:\s*(.*)\"\s*$", line, re.I | re.S)
    if not m:
        return None, f"{source}:{lineno}: GUIDE line does not follow the /fb inbox shape"
    date, thread, area, note = m.group(1), m.group(2), m.group(3), m.group(4).strip()
    head = note[:60].lower()
    verdict = next((v for v in VERDICTS if v in head), None)
    step = STEP.search(note)
    return {
        "date": date, "step": ("E" + step.group(1)) if step else "E?", "harness": f"{thread} · {area}",
        "verdict": verdict or "unclassified", "note": note, "evidence": "",
        "source": f"{source}:{lineno}", "origin": "fb",
    }, None


def load(since=None):
    findings, errors = [], []
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as f:
            in_inbox = False
            for i, raw in enumerate(f, 1):
                line = raw.rstrip("\n")
                if line.startswith("## "):
                    in_inbox = line.strip() == "## Inbox"
                    continue
                if in_inbox and line.startswith("- "):
                    item, err = parse_log_line(line, LOG, i)
                    (findings.append(item) if item else errors.append(err))
    else:
        errors.append(f"missing log: {LOG}")
    seen = set()
    for pattern in FEEDBACK_GLOBS:
        for path in sorted(glob.glob(pattern)):
            if path in seen:
                continue
            seen.add(path)
            with open(path, encoding="utf-8") as f:
                for i, raw in enumerate(f, 1):
                    if raw.startswith("- ") and re.search(r'"GUIDE:', raw, re.I):
                        item, err = parse_fb_line(raw.rstrip("\n"), path, i)
                        (findings.append(item) if item else errors.append(err))
    if since:
        findings = [x for x in findings if x["date"] >= since]
    return findings, errors


def report(findings):
    out = []
    counts = {v: sum(1 for x in findings if x["verdict"] == v) for v in VERDICTS}
    counts["unclassified"] = sum(1 for x in findings if x["verdict"] == "unclassified")
    out.append("# Guide findings compile")
    out.append("")
    out.append("| contradicts | adds | held | unclassified | total |")
    out.append("|---|---|---|---|---|")
    out.append(f"| {counts['contradicts']} | {counts['adds']} | {counts['held']} | {counts['unclassified']} | {len(findings)} |")
    for verdict in list(VERDICTS) + ["unclassified"]:
        group = [x for x in findings if x["verdict"] == verdict]
        if not group:
            continue
        out.append("")
        out.append(f"## {verdict} ({len(group)})")
        for step in sorted({x["step"] for x in group}, key=lambda s: (s == "E?", int(s[1:]) if s[1:].isdigit() else 99)):
            out.append("")
            out.append(f"### {step}")
            for x in sorted((g for g in group if g["step"] == step), key=lambda g: g["date"]):
                ev = f" Evidence: {x['evidence']}" if x["evidence"] else ""
                out.append(f"- {x['date']} · {x['harness']} · {x['note']}{ev} (from {x['origin']}, {os.path.basename(x['source'].split(':')[0])})")
    held = [x for x in findings if x["verdict"] == "held"]
    if held:
        out.append("")
        out.append("## Verified-column candidates (held, by harness)")
        out.append("")
        out.append("| Harness and model | Latest date | Count |")
        out.append("|---|---|---|")
        by = {}
        for x in held:
            by.setdefault(x["harness"], []).append(x["date"])
        for h, dates in sorted(by.items()):
            out.append(f"| {h} | {max(dates)} | {len(dates)} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate every line and exit 1 on a malformed one")
    ap.add_argument("--since", help="only findings dated on or after YYYY-MM-DD")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    a = ap.parse_args()
    findings, errors = load(a.since)
    for e in errors:
        print(f"MALFORMED: {e}", file=sys.stderr)
    if a.check:
        print(f"{len(findings)} findings parsed, {len(errors)} malformed", file=sys.stderr)
        sys.exit(1 if errors else 0)
    print(json.dumps(findings, indent=2) if a.json else report(findings))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
