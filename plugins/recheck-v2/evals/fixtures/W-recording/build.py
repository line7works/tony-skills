#!/usr/bin/env python3
"""Generator for the W-recording fixture lane (E7). CASES.md is the specification.

Standard library only, Python 3.9. Uses the shared library in ../_lib/fixturelib.py; git runs
only inside the throwaway repositories the library creates under --out.
"""
import copy
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "_lib"))

from fixturelib import GIT_BASE_DATE, GIT_FIX_DATE, Fixture, canonical_json, make_lane, sha256_hex  # noqa: E402

LANE = "W-recording"
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
DOC = "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC)
EXPORT = "src/widget/export.py"
REVIEW_DATE = "2026-09-19"
RUN_DATE = "2026-09-21"
HEADING_A = "### %s — review: Slice A" % REVIEW_DATE
HEADING_B = "### %s — review: Slice B" % REVIEW_DATE

BASE_MESSAGE = "Slice A: CSV export with review findings"
BASE_MESSAGE_AB = "Slices A and B: CSV export with review findings"
FIX_MESSAGE = "Quote CSV titles that need escaping"

README = """# widget
A tiny inventory export tool.
Run: `PYTHONPATH=src python3 -m widget.export <title> <qty>`
"""

GITIGNORE = "__pycache__/\n*.pyc\n.venv/\n"

# ---- code variants -------------------------------------------------------------------------

V_BASE = '''"""CSV export for widget inventory rows."""
import csv
import io
import sys


def format_title(title):
    """Return the title as it appears in the CSV title column."""
    return title


def format_qty(qty):
    """Return the quantity as it appears in the CSV qty column."""
    return str(qty)


def to_csv(rows):
    """Render (title, qty) rows as CSV text with a header line."""
    lines = ["title,qty"]
    for title, qty in rows:
        lines.append(format_title(title) + "," + format_qty(qty))
    return "\\n".join(lines) + "\\n"


def column_counts(text):
    """Column count of every line of a CSV text, header included."""
    return [len(row) for row in csv.reader(io.StringIO(text))]


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: python3 -m widget.export <title> <qty>\\n")
        return 2
    try:
        text = to_csv([(argv[1], argv[2])])
    except ValueError as err:
        sys.stderr.write("error: " + str(err) + "\\n")
        return 1
    sys.stdout.write(text)
    sys.stdout.write("columns=" + ",".join(str(n) for n in column_counts(text)) + "\\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''

TITLE_BASE = '''def format_title(title):
    """Return the title as it appears in the CSV title column."""
    return title
'''

TITLE_COMMA = '''def format_title(title):
    """Return the title as it appears in the CSV title column."""
    if "," in title or '"' in title:
        return '"' + title.replace('"', '""') + '"'
    return title
'''

TITLE_COMMA_NEWLINE = '''def format_title(title):
    """Return the title as it appears in the CSV title column."""
    if "," in title or '"' in title or "\\n" in title:
        return '"' + title.replace('"', '""') + '"'
    return title
'''

QTY_BASE = '''def format_qty(qty):
    """Return the quantity as it appears in the CSV qty column."""
    return str(qty)
'''

QTY_NEG = '''def format_qty(qty):
    """Return the quantity as it appears in the CSV qty column."""
    if str(qty).lstrip("-").isdigit() and int(qty) < 0:
        raise ValueError("qty must be zero or more, got " + str(qty))
    return str(qty)
'''

V_COMMA = V_BASE.replace(TITLE_BASE, TITLE_COMMA)
V_COMMA_NEWLINE = V_BASE.replace(TITLE_BASE, TITLE_COMMA_NEWLINE)
V_NEG = V_BASE.replace(QTY_BASE, QTY_NEG)
V_ALL = V_COMMA.replace(QTY_BASE, QTY_NEG)

# ---- ledger entries ------------------------------------------------------------------------

E1 = {"severity": "BLOCKER", "file": EXPORT, "line": 9,
      "claim": "CSV export writes an unescaped comma inside the title column",
      "scenario": 'PYTHONPATH=src python3 -m widget.export "Widgets, large" 3 prints a data row that parses to three columns (columns=2,3)',
      "slice": "A", "heading": HEADING_A}
E2 = {"severity": "MAJOR", "file": EXPORT, "line": 14,
      "claim": "a negative qty is exported unchanged",
      "scenario": "PYTHONPATH=src python3 -m widget.export Widget -3 prints Widget,-3 and exits 0",
      "slice": "A", "heading": HEADING_A}
E3 = {"severity": "MAJOR", "file": EXPORT, "line": 21,
      "claim": "a title containing a newline is exported as two rows",
      "scenario": "PYTHONPATH=src python3 -m widget.export \"$(printf 'Widget\\nlarge')\" 3 prints columns=2,1,2",
      "slice": "B", "heading": HEADING_B}
E4 = {"severity": "MINOR", "file": EXPORT, "line": 32,
      "claim": "the usage message omits what the exit status means",
      "scenario": "PYTHONPATH=src python3 -m widget.export prints one usage line on stderr and exits 2 with nothing explaining the status",
      "slice": "A", "heading": HEADING_A}

HOW_E1 = ('executed PYTHONPATH=src python3 -m widget.export "Widgets, large" 3; the data row reads '
          '"Widgets, large",3 and columns=2,2; format_title now at src/widget/export.py:7-11')
HOW_E2 = ("executed PYTHONPATH=src python3 -m widget.export Widget -3; stderr reads error: qty must be "
          "zero or more, got -3 and the exit status is 1; format_qty now at src/widget/export.py:14-18")
HOW_E3 = ("executed PYTHONPATH=src python3 -m widget.export \"$(printf 'Widget\\nlarge')\" 3; the output "
          "is one quoted data row and columns=2,2")
HOW = {"E1": HOW_E1, "E2": HOW_E2, "E3": HOW_E3}

EARLIER_RECHECK_HOW = "ran python3 -m widget.export Widget -3, exit 1 with error: qty must be zero or more, got -3"

G_REOPEN_E2 = {
    "item": {"location": {"file": EXPORT, "line": 14}, "claim": E2["claim"]},
    "by": "user", "channel": "user-turn", "turn_ref": "claude-code:session w2:turn 2",
    "quoted_words": "reopen the negative qty one, I want it rechecked", "date": RUN_DATE,
}
G_WAIVE_E4 = {
    "item": {"location": {"file": EXPORT, "line": 32}, "claim": E4["claim"]},
    "by": "user", "channel": "user-turn", "turn_ref": "claude-code:session w2:turn 3",
    "quoted_words": "waive the usage message one, the exit status note can wait", "date": RUN_DATE,
    "severity": "MINOR",
}
G_WAIVE_E1 = {
    "item": {"location": {"file": EXPORT, "line": 9}, "claim": E1["claim"]},
    "by": "user", "channel": "user-turn", "turn_ref": "claude-code:session w2:turn 2",
    "quoted_words": "waive the comma one either way, I am happy with the quoting", "date": RUN_DATE,
    "severity": "BLOCKER",
}

PROSE_A = ("Slice A adds `widget.export`: a `to_csv` renderer for (title, qty) rows and a small CLI that\n"
           "prints the rendered text followed by the parsed column count of each line.")
PROSE_B = "Slice B rejects quantities and titles the CSV cannot carry as one row."

SLICES_A = [{"name": "A", "title": "CSV export", "status": "rejected"}]
SLICES_AB = SLICES_A + [{"name": "B", "title": "Quantity and title validation", "status": "rejected"}]

UTIL_PY = '''"""Small helpers shared by widget modules."""
import os
import re

TITLE_RE = re.compile(r"\\S")


def has_title(text):
    """True when the text holds at least one non-space character."""
    return bool(TITLE_RE.search(text))
'''

NOTES_MD = """# Working notes

- TODO: drop the `has_title` helper once the CLI validates titles itself.
- The header is fixed as `title,qty`; a `total` column is a later slice.
"""

W3_01_DOC = """# Widget export

## Slice A — CSV export
Status: rejected

Slice A adds `widget.export`: a `to_csv` renderer for (title, qty) rows and a small CLI that
prints the rendered text followed by the parsed column count of each line. The header reads
`title,qty`; the design sketch wrote it as title · qty.

## Notes

- Column order: title · qty · (total, in a later slice)
- Rendering order: header · rows · trailing newline

## Punch list

### 2026-09-19 — review: Slice A
- BLOCKER · src/widget/export.py:9 (csv) · CSV export writes an unescaped comma inside the title column · PYTHONPATH=src python3 -m widget.export "Widgets, large" 3 prints a data row that parses to three columns (columns=2,3) · Slice A
- MAJOR · src/widget/export.py:14 · PYTHONPATH=src python3 -m widget.export Widget -3 prints Widget,-3 and exits 0 · Slice A
- MINOR · src/widget/export.py:32 · the usage message omits what the exit status means · PYTHONPATH=src python3 -m widget.export prints one usage line on stderr and exits 2 with nothing explaining the status · Slice A
"""

W3_03_DOC = """# Widget export

## Slice A — CSV export
Status: rejected

Slice A adds `widget.export`: a `to_csv` renderer for (title, qty) rows and a small CLI that
prints the rendered text followed by the parsed column count of each line. Review blocks in
this doc follow the loop's shape, for example:

```markdown
### 2026-09-18 — review: Slice A
- MINOR · src/widget/export.py:1 · example claim · example scenario · Slice A
```

## Punch list

### 2026-09-19 — review: Slice A
- BLOCKER · src/widget/export.py:9 · CSV export writes an unescaped comma inside the title column · PYTHONPATH=src python3 -m widget.export "Widgets, large" 3 prints a data row that parses to three columns (columns=2,3) · Slice A

### Fixer notes
- MAJOR · src/widget/export.py:14 · a negative qty is exported unchanged · PYTHONPATH=src python3 -m widget.export Widget -3 prints Widget,-3 and exits 0 · Slice A
- The negative-qty line above is a note from the fixer, kept here until a reviewer records it.
"""

SEP = " · "


# ---- helpers -------------------------------------------------------------------------------

def dump_json(doc) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def loc(entry) -> str:
    return "%s:%s" % (entry["file"], entry["line"])


def write_shared(fx: Fixture) -> None:
    fx.write("README.md", README)
    fx.write(".gitignore", GITIGNORE)
    fx.write_bytes("src/widget/__init__.py", b"")


def write_doc_d1(fx: Fixture, findings: list) -> None:
    fx.build_doc(TOPIC, DOC_DATE, "Widget export", SLICES_A, prose={"A": PROSE_A})
    fx.review_block(DOC, REVIEW_DATE, "A", findings)


def write_doc_d2(fx: Fixture) -> None:
    fx.build_doc(TOPIC, DOC_DATE, "Widget export", SLICES_AB, prose={"A": PROSE_A, "B": PROSE_B})
    fx.review_block(DOC, REVIEW_DATE, "A", [E1])
    fx.review_block(DOC, REVIEW_DATE, "B", [E3])


def two_commits(fx: Fixture, findings: list, fix_variant: str) -> str:
    """Base commit (V-base, D1 with the findings) then the fix commit; returns HEAD."""
    write_shared(fx)
    fx.write(EXPORT, V_BASE)
    write_doc_d1(fx, findings)
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write(EXPORT, fix_variant)
    return fx.commit(FIX_MESSAGE, GIT_FIX_DATE)


def default_input(fx: Fixture, resume: bool = False) -> dict:
    return {
        "protocol_version": 1,
        "invocation": {"mode": "interactive", "caller": "direct", "run_id": "%s-run" % fx.case_id,
                       "run_dir": fx.run_dir, "resume": resume},
        "workspace": fx.workspace,
        "target": {"build_doc": DOC, "slice": "A"},
    }


def checklist_item(entry) -> dict:
    return {
        "severity": entry["severity"],
        "location": {"file": entry["file"], "line": entry["line"]},
        "claim": entry["claim"],
        "failure_scenario": entry["scenario"],
        "record": {"document": DOC, "heading": entry["heading"], "date": REVIEW_DATE},
        "slice": entry["slice"],
    }


def item_result(fx: Fixture, entry, how: str, reopened: dict = None) -> dict:
    result = {
        "severity": entry["severity"],
        "location": {"file": entry["file"], "line": entry["line"]},
        "claim": entry["claim"],
        "failure_scenario": entry["scenario"],
        "slice": entry["slice"],
    }
    if reopened is not None:
        result["reopened"] = {"date": reopened["date"], "quoted_words": reopened["quoted_words"],
                              "turn_ref": reopened["turn_ref"]}
    result["disposition"] = "fixed"
    result["verification"] = {"method": "executed", "evidence": [
        {"kind": "command", "detail": how, "artifact_path": os.path.join(fx.run_dir, "verifier", "raw.md")}]}
    result["adjudication"] = {"verifier_said": "fixed", "driver_action": "confirmed", "session_wrote_fix": False}
    return result


def doc_bytes(fx: Fixture) -> bytes:
    with open(os.path.join(fx.workspace, DOC), "rb") as fh:
        return fh.read()


def apply_step(fx: Fixture, step: dict) -> None:
    kind = step["kind"]
    if kind == "reopened_line":
        g = step["grant"]
        fx.reopen_line(DOC, g["date"], g["item"]["location"]["file"], g["item"]["location"]["line"],
                       g["item"]["claim"], g["quoted_words"])
    elif kind == "punch_list_block":
        fx.recheck_block(DOC, RUN_DATE, step["slice_name"],
                         [{"severity": e["severity"], "file": e["file"], "line": e["line"], "claim": e["claim"],
                           "disposition": "fixed", "how": HOW[key]} for key, e in step["entries"]])
    elif kind == "waived_line":
        g = step["grant"]
        fx.waiver_line(DOC, g["date"], g["severity"], g["item"]["location"]["file"],
                       g["item"]["location"]["line"], g["item"]["claim"], g["quoted_words"])
    elif kind == "status_line":
        fx.set_status(DOC, step["slice"], step["after"])
    else:
        raise ValueError("unknown step kind %r" % kind)


def seed_transaction(fx: Fixture, items: list, steps: list, done_steps: int, intent_steps: int,
                     landed_steps: int, grants: dict = None, named_items: list = None,
                     authorization: dict = None) -> None:
    """Pre-seed run/ for a run that stopped inside its recording transaction.

    items: [(key, entry, reopened_grant_or_None)] in checklist order.
    steps: plan steps in order (dicts with kind and its parameters), all targeting DOC.
    done_steps: how many steps carry both intent and done entries.
    intent_steps: how many steps carry an intent entry (>= done_steps).
    landed_steps: how many steps are applied to the working tree at build time.
    """
    grants = grants or {}
    run_id = "%s-run" % fx.case_id
    start_identity = fx.identity()

    # The plan: apply every step in sequence, hashing the target before and after each.
    contents = [doc_bytes(fx)]
    for step in steps:
        apply_step(fx, step)
        contents.append(doc_bytes(fx))
    plan = []
    for k, step in enumerate(steps, start=1):
        plan.append({"step": k, "kind": step["kind"], "target": DOC,
                     "before_sha256": sha256_hex(contents[k - 1]),
                     "after_sha256": sha256_hex(contents[k])})
    # Leave the working tree at the state after the landed steps.
    fx.write_bytes(DOC, contents[landed_steps])

    # The resolved input of the original run and the resume input of this case.
    original = default_input(fx, resume=False)
    resumed = default_input(fx, resume=True)
    for doc in (original, resumed):
        if named_items is not None:
            doc["named_items"] = copy.deepcopy(named_items)
        if authorization is not None:
            doc["authorization"] = copy.deepcopy(authorization)
    fx.run_file("input.json", dump_json(original))

    checklist = [checklist_item(e) for _, e, _ in items]
    fx.run_file("checklist.md", "# Checklist for %s\n" % run_id + "".join(
        "- " + SEP.join([e["severity"], loc(e), e["claim"], e["scenario"]]) + "\n" for _, e, _ in items))
    fx.run_file("verifier/raw.md", "# Verifier report\n" + "".join(
        SEP.join([loc(e), "fixed", HOW[key]]) + "\n" for key, e, _ in items))

    body = copy.deepcopy(original)
    body.pop("invocation", None)
    input_sha = sha256_hex(canonical_json(body))
    n = len(items)
    pending = {"state": "pending", "retries": 0}
    ck = {
        "protocol_version": 1,
        "run_id": run_id,
        "run_dir": fx.run_dir,
        "phase": "assembling",
        "input_sha256": input_sha,
        "start_identity": start_identity,
        "scope": {
            "checklist": checklist,
            "grants": {"waivers": copy.deepcopy(grants.get("waivers", [])),
                       "reopenings": copy.deepcopy(grants.get("reopenings", [])),
                       "rejected": []},
            "review_sheet": "absent",
        },
        "items": [dict(pending) for _ in items],
        "new_defects": [],
        "verifier_calls": [],
        "continuations": 0,
    }
    fx.checkpoint(copy.deepcopy(ck))                                   # seq 0
    ck["phase"] = "verifying"
    ck["verifier_calls"] = [{"call_id": "%s-verify" % run_id, "status": "complete", "items": list(range(n))}]
    fx.checkpoint(copy.deepcopy(ck))                                   # seq 1
    ck["phase"] = "adjudicating"
    for k, (key, e, reopened) in enumerate(items):
        ck["items"][k] = {"state": "done", "retries": 0, "result": item_result(fx, e, HOW[key], reopened)}
        fx.checkpoint(copy.deepcopy(ck))                               # seq 2 .. 1+n
    ck["phase"] = "recording"
    fx.checkpoint(copy.deepcopy(ck))                                   # seq 2+n

    rc = {"run_id": run_id, "phase": "recording", "plan": plan, "entries": []}
    fx.receipt(copy.deepcopy(rc))                                      # seq 0
    for k in range(1, intent_steps + 1):
        rc["entries"].append({"step": k, "type": "intent"})
        fx.receipt(copy.deepcopy(rc))
        if k <= done_steps:
            rc["entries"].append({"step": k, "type": "done", "observed_sha256": plan[k - 1]["after_sha256"]})
            fx.receipt(copy.deepcopy(rc))
            fx.checkpoint(copy.deepcopy(ck))                           # one write per receipted done step

    fx.write_input(resumed)


# ---- cases ---------------------------------------------------------------------------------

def w1_01(fx: Fixture) -> None:
    fx.checks = ["W1"]
    write_shared(fx)
    fx.write(EXPORT, V_BASE)
    fx.write("src/widget/util.py", UTIL_PY)
    fx.write("docs/notes.md", NOTES_MD)
    write_doc_d1(fx, [E1])
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write(EXPORT, V_COMMA)
    fx.commit(FIX_MESSAGE, GIT_FIX_DATE)
    os.makedirs(os.path.join(fx.workspace, "docs", "reviews"))
    fx.write_input(default_input(fx))
    fx.manifest(notes="HEAD the fix commit, tree clean; util.py with an unused import, docs/notes.md with a TODO, an empty docs/reviews/ directory; run/ empty")


def w2_01(fx: Fixture) -> None:
    fx.checks = ["W2"]
    write_shared(fx)
    fx.write(EXPORT, V_BASE)
    write_doc_d1(fx, [E1, E2, E4])
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write(EXPORT, V_NEG)
    fx.recheck_block(DOC, "2026-09-20", "A", [{"severity": "MAJOR", "file": EXPORT, "line": 14, "claim": E2["claim"],
                                              "disposition": "fixed", "how": EARLIER_RECHECK_HOW}])
    fx.commit("Reject negative quantities", GIT_FIX_DATE)
    fx.write(EXPORT, V_ALL)
    fx.commit(FIX_MESSAGE, fx.next_when())
    steps = [
        {"kind": "reopened_line", "grant": G_REOPEN_E2},
        {"kind": "punch_list_block", "slice_name": "A", "entries": [("E1", E1), ("E2", E2)]},
        {"kind": "waived_line", "grant": G_WAIVE_E4},
        {"kind": "status_line", "slice": "A", "after": "signed off"},
    ]
    seed_transaction(fx, [("E1", E1, None), ("E2", E2, G_REOPEN_E2)], steps,
                     done_steps=2, intent_steps=3, landed_steps=2,
                     grants={"waivers": [G_WAIVE_E4], "reopenings": [G_REOPEN_E2]},
                     named_items=[G_REOPEN_E2["item"]],
                     authorization={"reopen": [G_REOPEN_E2], "waivers": [G_WAIVE_E4]})
    fx.manifest(notes="three commits, HEAD V-all; steps 1 (reopened line) and 2 (block) landed with done entries, step 3 (waiver) has an intent entry only; checkpoint seq 6, receipt seq 5; resume input")


def w2_02(fx: Fixture) -> None:
    fx.checks = ["W2"]
    two_commits(fx, [E1], V_COMMA)
    steps = [
        {"kind": "punch_list_block", "slice_name": "A", "entries": [("E1", E1)]},
        {"kind": "status_line", "slice": "A", "after": "signed off"},
    ]
    seed_transaction(fx, [("E1", E1, None)], steps, done_steps=1, intent_steps=2, landed_steps=2)
    fx.manifest(notes="HEAD the fix commit; steps 1 (block) and 2 (status line) landed on disk, step 2 has an intent entry and no done entry; checkpoint seq 4, receipt seq 3; resume input")


def w2_03(fx: Fixture) -> None:
    fx.checks = ["W2"]
    write_shared(fx)
    fx.write(EXPORT, V_BASE)
    write_doc_d2(fx)
    fx.commit(BASE_MESSAGE_AB, GIT_BASE_DATE)
    fx.write(EXPORT, V_COMMA_NEWLINE)
    fx.commit(FIX_MESSAGE, GIT_FIX_DATE)
    steps = [
        {"kind": "punch_list_block", "slice_name": "A, Slice B", "entries": [("E1", E1), ("E3", E3)]},
        {"kind": "status_line", "slice": "A", "after": "signed off"},
        {"kind": "status_line", "slice": "B", "after": "signed off"},
    ]
    seed_transaction(fx, [("E1", E1, None), ("E3", E3, None)], steps, done_steps=2, intent_steps=3, landed_steps=2,
                     named_items=[{"location": {"file": EXPORT, "line": 21}, "claim": E3["claim"]}])
    fx.manifest(notes="two slices, HEAD V-comma-newline; the block and the Slice A status line landed with done entries, the Slice B status line has an intent entry only; checkpoint seq 6, receipt seq 5; resume input")


def w2_04(fx: Fixture) -> None:
    fx.checks = ["W2"]
    two_commits(fx, [E1], V_COMMA)
    steps = [
        {"kind": "punch_list_block", "slice_name": "A", "entries": [("E1", E1)]},
        {"kind": "status_line", "slice": "A", "after": "signed off"},
    ]
    seed_transaction(fx, [("E1", E1, None)], steps, done_steps=1, intent_steps=2, landed_steps=1)
    marker = "prints the rendered text followed by the parsed column count of each line.\n"
    text = fx.read(DOC)
    if text.count(marker) != 1:
        raise ValueError("Slice A prose sentence not found once in %s" % DOC)
    fx.write(DOC, text.replace(marker, marker + "The header order is fixed as title, qty.\n"))
    fx.manifest(notes="HEAD the fix commit; step 1 (block) landed with a done entry, step 2 (status line) has an intent entry and its Status line is unchanged; one prose line added to Slice A outside the run; checkpoint seq 4, receipt seq 3; resume input")


def w2_05(fx: Fixture) -> None:
    fx.checks = ["W2"]
    two_commits(fx, [E1], V_COMMA)
    steps = [
        {"kind": "punch_list_block", "slice_name": "A", "entries": [("E1", E1)]},
        {"kind": "waived_line", "grant": G_WAIVE_E1},
        {"kind": "status_line", "slice": "A", "after": "signed off"},
    ]
    seed_transaction(fx, [("E1", E1, None)], steps, done_steps=0, intent_steps=1, landed_steps=1,
                     grants={"waivers": [G_WAIVE_E1]}, authorization={"waivers": [G_WAIVE_E1]})
    fx.manifest(notes="HEAD the fix commit; step 1 (block) landed on disk with an intent entry only, steps 2 (waiver line) and 3 (status line) target the same document and have no entries; checkpoint seq 3, receipt seq 1; resume input")


def w3_01(fx: Fixture) -> None:
    fx.checks = ["W3"]
    write_shared(fx)
    fx.write(EXPORT, V_BASE)
    fx.write(DOC, W3_01_DOC)
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write(EXPORT, V_ALL)
    fx.waiver_line(DOC, "2026-09-20", "MINOR", EXPORT, 32, E4["claim"])
    fx.commit("Quote titles, reject negative qty, record the usage waiver", GIT_FIX_DATE)
    fx.write_input(default_input(fx))
    fx.manifest(notes="HEAD the fix commit (V-all), tree clean; ledger with a tagged location, a claim-less finding, a MINOR finding, and a legacy waiver without words; prose and Notes bullets with the separator outside the ledger; run/ empty")


def w3_02a(fx: Fixture) -> None:
    fx.checks = ["W3"]
    two_commits(fx, [{"severity": "BLOCKER", "file": EXPORT, "line": 9,
                      "claim": "CSV export writes an unescaped comma · title and qty merge into three columns",
                      "scenario": E1["scenario"]}], V_COMMA)
    fx.write_input(default_input(fx))
    fx.manifest(notes="HEAD the fix commit, tree clean; the one ledger line splits into six fields on the separator; run/ empty")


def w3_02b(fx: Fixture) -> None:
    fx.checks = ["W3"]
    write_shared(fx)
    fx.write(EXPORT, V_BASE)
    fx.build_doc(TOPIC, DOC_DATE, "Widget export", SLICES_A, prose={"A": PROSE_A})
    fx.raw_ledger_line(DOC, "\n%s\n- BLOCKER · src/widget/export.py:9\n" % HEADING_A)
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write(EXPORT, V_COMMA)
    fx.commit(FIX_MESSAGE, GIT_FIX_DATE)
    fx.write_input(default_input(fx))
    fx.manifest(notes="HEAD the fix commit, tree clean; the one ledger line has two fields (severity, location); run/ empty")


def w3_02c(fx: Fixture) -> None:
    fx.checks = ["W3"]
    two_commits(fx, [E1, E1], V_COMMA)
    fx.write_input(default_input(fx))
    fx.manifest(notes="HEAD the fix commit, tree clean; the review block holds two byte-identical lines; run/ empty")


def w3_02d(fx: Fixture) -> None:
    fx.checks = ["W3"]
    write_shared(fx)
    fx.write(EXPORT, V_BASE)
    write_doc_d1(fx, [E1, E2])
    fx.raw_ledger_line(DOC, "- " + SEP.join(["WAIVED (per user)", "MAJOR", loc(E2), E2["claim"],
                                             '"skip the negative qty check for now"']) + "\n")
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write(EXPORT, V_COMMA)
    fx.commit(FIX_MESSAGE, GIT_FIX_DATE)
    fx.write_input(default_input(fx))
    fx.manifest(notes="HEAD the fix commit, tree clean; a waiver line with five fields whose second field is a severity, directly after E2; run/ empty")


def w3_03(fx: Fixture) -> None:
    fx.checks = ["W3"]
    write_shared(fx)
    fx.write(EXPORT, V_BASE)
    fx.write(DOC, W3_03_DOC)
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write(EXPORT, V_COMMA)
    fx.commit(FIX_MESSAGE, GIT_FIX_DATE)
    fx.write_input(default_input(fx))
    fx.manifest(notes="HEAD the fix commit, tree clean; a block heading and a finding line inside a fenced code block in the prose, a Fixer notes heading with a finding-shaped bullet inside the Punch list section; run/ empty")


def w4_01(fx: Fixture) -> None:
    fx.checks = ["W4"]
    two_commits(fx, [E1], V_COMMA)
    fx.write_input(default_input(fx))
    fx.manifest(trial_conditions={"tracked_edit_between_steps": {
        "after_step": 1, "before_step": 2, "file": EXPORT, "line": 34,
        "text": '        sys.stderr.write("usage: python3 -m widget.export TITLE QTY\\n")'}},
        notes="HEAD the fix commit, tree clean, run/ empty; the harness edits line 34 of src/widget/export.py between the done entry of step 1 and the intent entry of step 2")


CASES = {
    "W1-01-authorized-writes-only": w1_01,
    "W2-01-between-steps": w2_01,
    "W2-02-landed-without-done": w2_02,
    "W2-03-between-two-status-lines": w2_03,
    "W2-04-outside-edit": w2_04,
    "W2-05-two-steps-same-target": w2_05,
    "W3-01-legacy-round-trip": w3_01,
    "W3-02a-claim-with-separator": w3_02a,
    "W3-02b-no-shape-field-count": w3_02b,
    "W3-02c-duplicate-findings": w3_02c,
    "W3-02d-waiver-without-date": w3_02d,
    "W3-03-embedded-record-syntax": w3_03,
    "W4-01-boundary-violation": w4_01,
}


if __name__ == "__main__":
    make_lane(LANE, CASES)
