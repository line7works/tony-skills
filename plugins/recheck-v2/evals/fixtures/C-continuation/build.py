#!/usr/bin/env python3
"""Generator for the C-continuation fixture lane (E7). See CASES.md for what each case holds.

Standard library only, Python 3.9. Uses the shared library in ../_lib/fixturelib.py; git runs
only inside the throwaway repositories the library creates under --out.
"""
import copy
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "_lib"))

from fixturelib import GIT_BASE_DATE, GIT_FIX_DATE, Fixture, canonical_json, make_lane, sha256_hex  # noqa: E402

LANE = "C-continuation"
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
DOC = "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC)
IMPORT_DOC = "docs/plans/%s-widget-import.md" % DOC_DATE
REVIEW_DATE = "2026-09-19"
REVIEW_HEADING = "### %s — review: Slice A" % REVIEW_DATE

BASE_MESSAGE = "Slice A: CSV export, review recorded"
FIX_MESSAGE = "Slice A: quote CSV fields, full header"

README = """# widget

The module `widget.export` renders widget rows as CSV lines.
"""

GITIGNORE = "__pycache__/\n*.pyc\n.venv/\n"

EXPORT_BASE = '''"""CSV export for widget rows."""
import argparse
import csv
import io

FIELDS = ("id", "title", "qty")


def parse_qty(text):
    """Turn the --qty argument into an integer."""
    return int(text)


def format_row(row):
    """Render one row as a CSV line."""
    return ",".join(str(row.get(k)) for k in FIELDS)


def header():
    """Render the header line."""
    return ",".join(FIELDS[:2])


def column_count(line):
    """Count the columns a CSV reader sees in one line."""
    return len(next(csv.reader(io.StringIO(line))))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="widget.export")
    parser.add_argument("--header", action="store_true")
    parser.add_argument("--id", default="1")
    parser.add_argument("--title")
    parser.add_argument("--qty", default="2")
    args = parser.parse_args(argv)
    if args.header:
        line = header()
    else:
        row = {"id": args.id, "qty": parse_qty(args.qty)}
        if args.title is not None:
            row["title"] = args.title
        line = format_row(row)
    print(line)
    print("columns=%d" % column_count(line))


if __name__ == "__main__":
    main()
'''

EXPORT_FIX = '''"""CSV export for widget rows."""
import argparse
import csv
import io

FIELDS = ("id", "title", "qty")


def parse_qty(text):
    """Turn the --qty argument into an integer."""
    return int(text)


def format_row(row):
    """Render one row as a CSV line."""
    return ",".join(quote(str(row.get(k))) for k in FIELDS)


def header():
    """Render the header line."""
    return ",".join(FIELDS)


def quote(value):
    """Wrap a value in double quotes when it holds a comma."""
    if "," in value:
        return '"' + value.replace('"', '""') + '"'
    return value


def column_count(line):
    """Count the columns a CSV reader sees in one line."""
    return len(next(csv.reader(io.StringIO(line))))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="widget.export")
    parser.add_argument("--header", action="store_true")
    parser.add_argument("--id", default="1")
    parser.add_argument("--title")
    parser.add_argument("--qty", default="2")
    args = parser.parse_args(argv)
    if args.header:
        line = header()
    else:
        row = {"id": args.id, "qty": parse_qty(args.qty)}
        if args.title is not None:
            row["title"] = args.title
        line = format_row(row)
    print(line)
    print("columns=%d" % column_count(line))


if __name__ == "__main__":
    main()
'''

SLICE_PROSE = (
    "Slice A renders widget rows as CSV lines through `widget.export.format_row` and a header\n"
    "line through `widget.export.header`. The CLI `python3 -m widget.export` prints one line and\n"
    "the column count a CSV reader sees."
)

IMPORT_DOC_TEXT = """# Widget import

## Slice A — CSV import
Status: rejected

Slice A is planned; no code exists for it yet.

## Punch list
"""

FINDINGS = [
    {"severity": "BLOCKER", "file": "src/widget/export.py", "line": 16,
     "claim": "CSV export writes unescaped commas inside quoted fields",
     "scenario": "export a row whose title contains a comma; the produced CSV has one extra column"},
    {"severity": "MAJOR", "file": "src/widget/export.py", "line": 11,
     "claim": "a negative quantity is accepted without error",
     "scenario": "export a row with --qty -1; the row is printed with -1 instead of the program exiting non-zero"},
    {"severity": "MAJOR", "file": "src/widget/export.py", "line": 21,
     "claim": "the header line omits the qty column",
     "scenario": "print the header with --header; it has two columns while rows have three"},
]

EXPORT_COMMA_LOG = '7,"Bolt, hex",3\ncolumns=3\n'

RAW_MD = """# Verifier report

Run {run_id}, call {run_id}-verify. Workspace: HEAD is the fix commit, work tree
clean. Review sheet: no REVIEW.md in the workspace root. Every scenario ran from the workspace
root with PYTHONPATH=src and /usr/bin/python3 (3.9.6). Nothing outbound, no other tool, no
write outside verifier/.

## Item 0: BLOCKER src/widget/export.py:16

Ran: PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3, stdout
redirected to verifier/export-comma.log. Exit status 0. Output: 7,"Bolt, hex",3 then
columns=3. Line 16 now reads return ",".join(quote(str(row.get(k))) for k in FIELDS) and a
quote helper at lines 24 to 28 wraps a value holding a comma in double quotes. Against the
scenario: the title is quoted, the reader sees three columns, and the row has no extra column.
The scenario no longer holds.

## Item 1: MAJOR src/widget/export.py:11

Ran: PYTHONPATH=src python3 -m widget.export --id 7 --title Bolt --qty -1. Exit status 0.
Output: 7,Bolt,-1 then columns=3. Line 11 still reads return int(text); nothing checks the
sign. Against the scenario: the row is printed with -1 and the program exits 0. The scenario
still holds.

## Item 2: MAJOR src/widget/export.py:21

Ran: PYTHONPATH=src python3 -m widget.export --header. Exit status 0. Output: id,title,qty
then columns=3. Line 21 now reads return ",".join(FIELDS). Against the scenario: the header
has three columns, the same count as a row. The scenario no longer holds.

Method for every item: executed.
"""

GRANT_WORDS = "go one more round on slice A"
GRANT_DATE = "2026-09-21"


# ---- helpers -------------------------------------------------------------------------------

def dump_json(doc) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def placeholder_digest(case_id: str, seq: int) -> str:
    return hashlib.sha256(("%s:%d\n" % (case_id, seq)).encode("utf-8")).hexdigest()


def checklist_items() -> list:
    items = []
    for f in FINDINGS:
        items.append({
            "severity": f["severity"],
            "location": {"file": f["file"], "line": f["line"]},
            "claim": f["claim"],
            "failure_scenario": f["scenario"],
            "record": {"document": DOC, "heading": REVIEW_HEADING, "date": REVIEW_DATE},
            "slice": "A",
        })
    return items


def make_workspace(fx: Fixture, with_import_doc: bool = False) -> str:
    """Base commit (defect present, review recorded) then the fix commit; returns HEAD."""
    fx.write("README.md", README)
    fx.write(".gitignore", GITIGNORE)
    fx.write_bytes("src/widget/__init__.py", b"")
    fx.write("src/widget/export.py", EXPORT_BASE)
    fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                 [{"name": "A", "title": "CSV export", "status": "rejected"}],
                 prose={"A": SLICE_PROSE})
    fx.review_block(DOC, REVIEW_DATE, "A", FINDINGS)
    if with_import_doc:
        fx.write(IMPORT_DOC, IMPORT_DOC_TEXT)
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write("src/widget/export.py", EXPORT_FIX)
    return fx.commit(FIX_MESSAGE, GIT_FIX_DATE)


def continuation_grant(turn_ref: str) -> dict:
    return {"by": "user", "channel": "user-turn", "turn_ref": turn_ref,
            "quoted_words": GRANT_WORDS, "date": GRANT_DATE}


def original_input(fx: Fixture, run_id: str, grant_turn: str = None) -> dict:
    doc = {
        "protocol_version": 1,
        "invocation": {"mode": "interactive", "caller": "direct", "run_id": run_id,
                       "run_dir": fx.run_dir, "resume": False},
        "workspace": fx.workspace,
        "target": {"build_doc": DOC, "slice": "A"},
    }
    if grant_turn is not None:
        doc["authorization"] = {"extra_continuation": continuation_grant(grant_turn)}
    return doc


def resume_input(fx: Fixture, build_doc: str = DOC, grant_turn: str = None) -> dict:
    doc = {
        "protocol_version": 1,
        "invocation": {"mode": "interactive", "caller": "direct", "run_id": "%s-run" % fx.case_id,
                       "run_dir": fx.run_dir, "resume": True},
        "workspace": fx.workspace,
        "target": {"build_doc": build_doc, "slice": "A"},
    }
    if grant_turn is not None:
        doc["authorization"] = {"extra_continuation": continuation_grant(grant_turn)}
    return doc


def binding_hash(inp: dict) -> str:
    """Appendix B carried item N6 (ruling E7-3): the input with `invocation` and
    `authorization.extra_continuation` removed; an `authorization` object left empty by
    that removal is dropped too."""
    body = copy.deepcopy(inp)
    body.pop("invocation", None)
    auth = body.get("authorization")
    if isinstance(auth, dict):
        auth.pop("extra_continuation", None)
        if not auth:
            body.pop("authorization")
    return sha256_hex(canonical_json(body))


def item0_result(fx: Fixture) -> dict:
    f = FINDINGS[0]
    return {
        "severity": f["severity"],
        "location": {"file": f["file"], "line": f["line"]},
        "claim": f["claim"],
        "failure_scenario": f["scenario"],
        "slice": "A",
        "disposition": "fixed",
        "verification": {"method": "executed", "evidence": [
            {"kind": "command",
             "detail": "PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3 printed 7,\"Bolt, hex\",3 and columns=3",
             "artifact_path": os.path.join(fx.run_dir, "verifier", "export-comma.log")},
            {"kind": "artifact",
             "detail": "the verifier's report, section Item 0: the title is quoted, the reader sees three columns, the scenario no longer holds",
             "artifact_path": os.path.join(fx.run_dir, "verifier", "raw.md")},
        ]},
        "adjudication": {"verifier_said": "fixed", "driver_action": "confirmed", "session_wrote_fix": False},
    }


def item1_done_result() -> dict:
    f = FINDINGS[1]
    return {
        "severity": f["severity"],
        "location": {"file": f["file"], "line": f["line"]},
        "claim": f["claim"],
        "failure_scenario": f["scenario"],
        "slice": "A",
        "disposition": "fixed",
        "verification": {"method": "executed", "evidence": [
            {"kind": "command",
             "detail": "PYTHONPATH=src python3 -m widget.export --id 7 --title Bolt --qty -1 printed 7,Bolt,-1"},
        ]},
        "adjudication": {"verifier_said": "fixed", "driver_action": "confirmed", "session_wrote_fix": False},
    }


def chain_documents(fx: Fixture, run_id: str, input_sha: str, start_identity: dict) -> list:
    """The four documents of the reference chain, seq 0 to 3, in write order."""
    pending = {"state": "pending", "retries": 0}
    call = {"call_id": "%s-verify" % run_id, "status": "complete", "items": [0, 1, 2]}
    doc0 = {
        "protocol_version": 1,
        "run_id": run_id,
        "run_dir": fx.run_dir,
        "phase": "assembling",
        "input_sha256": input_sha,
        "start_identity": start_identity,
        "scope": {
            "checklist": checklist_items(),
            "grants": {"waivers": [], "reopenings": [], "rejected": []},
            "review_sheet": "absent",
        },
        "items": [dict(pending), dict(pending), dict(pending)],
        "new_defects": [],
        "verifier_calls": [],
        "continuations": 0,
    }
    doc1 = copy.deepcopy(doc0)
    doc1["phase"] = "verifying"
    doc2 = copy.deepcopy(doc1)
    doc2["verifier_calls"] = [call]
    doc3 = copy.deepcopy(doc2)
    doc3["phase"] = "adjudicating"
    doc3["items"][0] = {"state": "done", "retries": 0, "result": item0_result(fx)}
    return [doc0, doc1, doc2, doc3]


def seed_run(fx: Fixture, run_id: str = None, build_doc_in_input: str = DOC, grant_turn: str = None,
             seq3_edit=None, seq3_kwargs=None, original_grant_turn: str = None):
    """Write the reference run/ directory and the resume input.

    Returns (documents, selfs): the chain documents as written (each carrying its integrity
    block) and the list of their self digests. seq3_edit, when given, is applied to the seq 3
    document before it is written; seq3_kwargs are passed to the library's checkpoint() for
    that write. grant_turn puts an extra_continuation grant on the resume input;
    original_grant_turn puts one on the saved original input (resolved-input.json).
    """
    run_id = run_id or "%s-run" % fx.case_id
    inp = original_input(fx, run_id, grant_turn=original_grant_turn)
    fx.run_file("resolved-input.json", dump_json(inp))
    fx.run_file("checklist.json", dump_json(checklist_items()))
    fx.run_file("verifier/export-comma.log", EXPORT_COMMA_LOG)
    fx.run_file("verifier/raw.md", RAW_MD.format(run_id=run_id))
    docs = chain_documents(fx, run_id, binding_hash(inp), fx.identity())
    if seq3_edit is not None:
        seq3_edit(docs[3])
    selfs = []
    for i, doc in enumerate(docs):
        kwargs = dict(seq3_kwargs or {}) if i == 3 else {}
        selfs.append(fx.checkpoint(doc, **kwargs))
    fx.write_input(resume_input(fx, build_doc=build_doc_in_input, grant_turn=grant_turn))
    return docs, selfs


def log_lines(fx: Fixture) -> list:
    return fx.read_run_file("checkpoint.log").splitlines()


def write_log(fx: Fixture, lines: list) -> None:
    fx.run_file("checkpoint.log", "\n".join(lines) + "\n")


def fifth_write(fx: Fixture, docs: list) -> None:
    """The C3 shape: one more write carrying continuations 1."""
    doc4 = copy.deepcopy(docs[3])
    doc4["continuations"] = 1
    fx.checkpoint(doc4)


# ---- cases ---------------------------------------------------------------------------------

def c2_01(fx: Fixture) -> None:
    fx.checks = ["C2"]
    make_workspace(fx)
    seed_run(fx)
    fx.manifest(trial_conditions={"fresh_session": True},
                notes="run/ in the reference form: checkpoint at phase adjudicating, item 0 done, items 1 and 2 pending, continuations 0, log seqs 0 to 3; resume input")


def c3_01(fx: Fixture) -> None:
    fx.checks = ["C3"]
    make_workspace(fx)
    docs, _ = seed_run(fx)
    fifth_write(fx, docs)
    fx.manifest(notes="five-write chain, seq 4 carries continuations 1; resume input without authorization")


def c3_02(fx: Fixture) -> None:
    fx.checks = ["C3"]
    make_workspace(fx)
    docs, _ = seed_run(fx, grant_turn="claude-code:session c302:turn 6")
    fifth_write(fx, docs)
    fx.manifest(notes="five-write chain, seq 4 carries continuations 1; resume input carries an extra_continuation grant on the user channel; resolved-input.json carries no grant")


def c3_03(fx: Fixture) -> None:
    fx.checks = ["C3"]
    make_workspace(fx)
    docs, _ = seed_run(fx, original_grant_turn="claude-code:session c303:turn 6")
    fifth_write(fx, docs)
    fx.manifest(notes="five-write chain, seq 4 carries continuations 1; resolved-input.json carries an extra_continuation grant on the user channel; input_sha256 computed over it minus invocation and the grant; the resume input carries no authorization key")


def c4_01(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx)
    docs, _ = seed_run(fx)
    doc = copy.deepcopy(docs[3])
    doc["items"][1]["retries"] = 1
    fx.run_file("checkpoint.json", dump_json(doc))
    fx.manifest(notes="checkpoint.json edited after signing (items[1].retries 1), integrity.self left as signed, log untouched")


def c4_02(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx)
    seed_run(fx, seq3_kwargs={"log": False})
    fx.manifest(notes="seq 3 checkpoint written without its log line; log holds seqs 0 to 2")


def c4_03(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx)
    # The seq 0 digest is needed before the seq 3 write; compute it from the chain documents.
    run_id = "%s-run" % fx.case_id
    inp = original_input(fx, run_id)
    docs = chain_documents(fx, run_id, binding_hash(inp), fx.identity())
    body = copy.deepcopy(docs[0])
    body["integrity"] = {"seq": 0, "prev": None}
    self0 = sha256_hex(canonical_json(body))
    seed_run(fx, seq3_kwargs={"prev": self0})
    fx.manifest(notes="seq 3 checkpoint carries prev equal to the seq 0 digest, re-signed, log line 3 carries that digest")


def c4_04(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx, with_import_doc=True)
    seed_run(fx, build_doc_in_input=IMPORT_DOC)
    fx.manifest(notes="run/ in the reference form bound to docs/plans/2026-09-18-widget-export.md; the resume input names docs/plans/2026-09-18-widget-import.md")


def c4_05(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx)

    def drop_adjudication(doc):
        del doc["items"][0]["result"]["adjudication"]

    seed_run(fx, seq3_edit=drop_adjudication)
    fx.manifest(notes="seq 3 checkpoint: items[0].result carries no adjudication object, signed and logged as written")


def c4_06(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx)
    docs, selfs = seed_run(fx)
    doc = copy.deepcopy(docs[3])
    doc["items"][1] = {"state": "done", "retries": 0, "result": item1_done_result()}
    fx.checkpoint(doc, seq=4, prev=selfs[3], log=False)
    fx.manifest(notes="checkpoint.json re-signed at seq 4 with item 1 done; log holds seqs 0 to 3 only")


def c4_07(fx: Fixture) -> None:
    fx.checks = ["C4", "C5"]
    make_workspace(fx)
    seed_run(fx)
    lines = log_lines(fx)
    lines[2] = "2 %s" % placeholder_digest(fx.case_id, 2)
    lines.append("4 %s" % placeholder_digest(fx.case_id, 4))
    write_log(fx, lines)
    fx.manifest(notes="checkpoint.json the reference seq 3 document; log line 2 replaced with a digest no file carries and a fifth line announcing seq 4 appended")


def c4_08(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx)
    seed_run(fx, run_id="%s-other" % fx.case_id)
    fx.manifest(notes="run/ computed for run id C4-08-run-id-mismatch-other; input.json carries run id C4-08-run-id-mismatch-run")


def c4_09(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx)
    seed_run(fx)
    lines = log_lines(fx)
    del lines[2]
    write_log(fx, lines)
    fx.manifest(notes="checkpoint.json the reference seq 3 document; log holds seqs 0, 1, 3")


def c5_01(fx: Fixture) -> None:
    fx.checks = ["C5"]
    make_workspace(fx)
    seed_run(fx)
    lines = log_lines(fx)
    lines.append("4 %s" % placeholder_digest(fx.case_id, 4))
    write_log(fx, lines)
    fx.manifest(notes="checkpoint.json the reference seq 3 document; log holds the reference four lines plus a fifth announcing seq 4 with a digest no file carries")


def c1_01(fx: Fixture) -> None:
    fx.checks = ["C1"]
    make_workspace(fx)
    seed_run(fx)
    fx.manifest(trial_conditions={"compaction": True},
                notes="run/ in the reference form: checkpoint at phase adjudicating, item 0 done, items 1 and 2 pending, continuations 0, log seqs 0 to 3; resume input")


def c4_10(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx)
    seed_run(fx)
    os.remove(os.path.join(fx.run_dir, "checkpoint.json"))
    fx.manifest(notes="run/ holds the reference form without checkpoint.json; log holds seqs 0 to 3")


def c4_11(fx: Fixture) -> None:
    fx.checks = ["C4"]
    make_workspace(fx)
    seed_run(fx)
    fx.run_file("checkpoint.json", '{\n  "protocol_version": 1,\n  "run_id": "%s-run",\n' % fx.case_id)
    fx.manifest(notes="checkpoint.json holds the first 75 bytes of the reference seq 3 document and nothing after; log holds seqs 0 to 3")


CASES = {
    "C2-01-handoff-run-dir": c2_01,
    "C3-01-limit-exceeded": c3_01,
    "C3-02-limit-with-grant": c3_02,
    "C3-03-grant-dropped-at-resume": c3_03,
    "C4-01-bad-digest": c4_01,
    "C4-02-checkpoint-ahead-of-log": c4_02,
    "C4-03-broken-chain": c4_03,
    "C4-04-altered-target": c4_04,
    "C4-05-altered-item-state": c4_05,
    "C4-06-resigned-ahead": c4_06,
    "C4-07-corrupt-earlier-plus-announced": c4_07,
    "C4-08-run-id-mismatch": c4_08,
    "C4-09-log-gap": c4_09,
    "C5-01-announced-never-landed": c5_01,
    "C1-01-compaction": c1_01,
    "C4-10-missing-checkpoint": c4_10,
    "C4-11-unparseable-checkpoint": c4_11,
}


if __name__ == "__main__":
    make_lane(LANE, CASES)
