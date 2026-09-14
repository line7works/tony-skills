# C-continuation: cases

Lane C-continuation of recheck-v2 E7 (lane contract section 7, "C-continuation"; checks C1 to
C5; requirements R20, R35, R41). Facts only: what each repo contains at each commit, what the
code does, what sits under `run/`, and how each file that deviates differs from the reference
form. Seventeen cases: the fourteen of the catalog, in catalog order (one renamed, see
"Renamed cases"), then three under "Added cases" (`C1-01-compaction`,
`C4-10-missing-checkpoint`, `C4-11-unparseable-checkpoint`).
Every record line below is written in the Appendix A grammar with the separator ` · ` (space,
U+00B7, space). Control-room rulings relied on are cited as `ruling E7-<n>`.

## Renamed cases

- `C3-03-grant-after-binding` is now `C3-03-grant-dropped-at-resume` (ruling E7-17, critic
  finding CR-23). Reason: after ruling E7-3 the catalog's C3-03 held the same `run/` and the
  same hash facts as C3-02 and differed from it in case id, `run_id`, and `turn_ref` only.
  The renamed case inverts where the grant sits: the saved original input carries it and
  the presented resume input does not. `run_id` is `C3-03-grant-dropped-at-resume-run`.

## Shared shape

### The workspace

Every case is the `widget` project of lane contract 5.4, five tracked files at HEAD
(`C4-04-altered-target` adds a sixth, named under that case):

```text
README.md
.gitignore                                  __pycache__/, *.pyc, .venv/
src/widget/__init__.py                      empty
src/widget/export.py                        the module under review
docs/plans/2026-09-18-widget-export.md      the build doc
```

(`.git/` is not counted; no REVIEW.md, no `docs/reviews/`, no untracked file.)

Commits: base `2026-09-19T09:00:00-07:00` (message `Slice A: CSV export, review recorded`),
fix `2026-09-20T09:00:00-07:00` (message `Slice A: quote CSV fields, full header`). HEAD is
the fix commit; the work tree is clean at HEAD in every case. The build doc is committed in
the base commit and is byte-identical in the fix commit (the fix commit changes
`src/widget/export.py` only). `README.md` is one heading and one sentence naming the module;
it holds no record-shaped text.

`src/widget/export.py` at the base commit, 48 lines:

```python
"""CSV export for widget rows."""
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
```

Line 11 is the `return` of `parse_qty`, line 16 the `return` of `format_row`, line 21 the
`return` of `header` (measured with `grep -n return` on the prototype).

Measured on the base commit with `/usr/bin/python3` 3.9.6 from the workspace root:

```text
$ PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3
7,Bolt, hex,3
columns=4
$ PYTHONPATH=src python3 -m widget.export --id 7 --title Bolt --qty -1
7,Bolt,-1
columns=3
$ PYTHONPATH=src python3 -m widget.export --header
id,title
columns=2
```

The fix commit rewrites `export.py` to 55 lines. Three changes: line 16 becomes
`    return ",".join(quote(str(row.get(k))) for k in FIELDS)`; line 21 becomes
`    return ",".join(FIELDS)`; a `quote` helper is inserted after `header` (lines 24 to 28):

```python
def quote(value):
    """Wrap a value in double quotes when it holds a comma."""
    if "," in value:
        return '"' + value.replace('"', '""') + '"'
    return value
```

`parse_qty` is unchanged; line 11 still reads `    return int(text)` and `int("-1")` returns
`-1` with no check on sign. Lines 1 to 22 hold the same functions at the same line numbers
as the base commit; `column_count` and `main` move down seven lines.

Measured on the fix commit:

```text
$ PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3
7,"Bolt, hex",3
columns=3
$ PYTHONPATH=src python3 -m widget.export --id 7 --title Bolt --qty -1
7,Bolt,-1
columns=3
$ PYTHONPATH=src python3 -m widget.export --header
id,title,qty
columns=3
```

### The build doc

`docs/plans/2026-09-18-widget-export.md`, identical in every case:

```markdown
# Widget export

## Slice A — CSV export
Status: rejected

Slice A renders widget rows as CSV lines through `widget.export.format_row` and a header
line through `widget.export.header`. The CLI `python3 -m widget.export` prints one line and
the column count a CSV reader sees.

## Punch list

### 2026-09-19 — review: Slice A
- BLOCKER · src/widget/export.py:16 · CSV export writes unescaped commas inside quoted fields · export a row whose title contains a comma; the produced CSV has one extra column · Slice A
- MAJOR · src/widget/export.py:11 · a negative quantity is accepted without error · export a row with --qty -1; the row is printed with -1 instead of the program exiting non-zero · Slice A
- MAJOR · src/widget/export.py:21 · the header line omits the qty column · print the header with --header; it has two columns while rows have three · Slice A
```

The ledger home is the `## Punch list` section; it holds exactly one block, the review block
dated 2026-09-19, three lines, three distinct locations. No recheck block, waiver, or
reopening line exists in any case.

### The original input (the run that wrote the checkpoint)

Saved as `run/resolved-input.json` in every case; field names from `input.schema.json`:

```json
{
  "protocol_version": 1,
  "invocation": {"mode": "interactive", "caller": "direct", "run_id": "<case-id>-run", "run_dir": "<OUT>/<case-id>/run", "resume": false},
  "workspace": "<OUT>/<case-id>/workspace",
  "target": {"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}
}
```

`named_items`, `source_identity`, `review_sheet`, `authorization`, and `policy` are omitted
in every case except `C3-03-grant-dropped-at-resume`, whose saved original input carries
`authorization.extra_continuation` (ruling E7-17; the grant is quoted under that case).
C3-01 and C3-02 keep the saved original input without a grant (ruling E7-3). For
`C4-08-run-id-mismatch` the saved copy carries the checkpoint's run id, named under that
case.

### The resume input (`<case>/input.json`)

The same document with `invocation.resume` set to `true`; `run_id` and `run_dir` unchanged.
Route direct; mode `interactive`; caller `direct`; target form `build_doc` plus `slice: A`;
no `named_items`; no pin; `review_sheet` omitted; no grants; default policy. Cases that add a
grant or change the target say so under the case. `manifest.json` records
`input_validates: true` for every case.

### The checklist (`run/checklist.json`)

A JSON array of the three review entries in file order, each in the `item` shape of
`input.schema.json` (`severity`, `location`, `claim`, `failure_scenario`, `record`, `slice`),
`record` being `{"document": "docs/plans/2026-09-18-widget-export.md", "heading": "### 2026-09-19 — review: Slice A", "date": "2026-09-19"}`
and `slice` `"A"`. Item 0 is the BLOCKER at `src/widget/export.py:16`, item 1 the MAJOR at
`:11`, item 2 the MAJOR at `:21`.

### The verifier scratch (`run/verifier/`)

Two files.

`run/verifier/export-comma.log`, the verbatim output of the first scenario at HEAD, redirected
by the verifier:

```text
7,"Bolt, hex",3
columns=3
```

`run/verifier/raw.md`, the first verifier's unedited report (contract section 5: the raw text
kept under `run_dir`; section 9 item 1: an artifact created before the transaction). One
call, covering all three checklist items. Its text, with `<case-id>` filled at build time and
no absolute path anywhere in it:

```markdown
# Verifier report

Run <case-id>-run, call <case-id>-run-verify. Workspace: HEAD is the fix commit, work tree
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
```

The report names no absolute path; the redirected file is named relative to the verifier's
scratch (`verifier/export-comma.log`). The report contains none of the banned strings of lane
contract section 3.

### The checkpoint (`run/checkpoint.json`, the reference form)

Field names and nesting follow `examples/checkpoint-partial.json` exactly. The reference
document, `<OUT>` and `<commit>` filled at build time (`<commit>` is the full hash of the fix
commit; `<empty>` is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, the
SHA-256 of the empty string):

```json
{
  "protocol_version": 1,
  "run_id": "<case-id>-run",
  "run_dir": "<OUT>/<case-id>/run",
  "phase": "adjudicating",
  "input_sha256": "<see Binding below>",
  "start_identity": {"commit": "<commit>", "dirty": false, "tracked_diff_sha256": "<empty>", "untracked": [], "untracked_sha256": "<empty>", "submodules": []},
  "scope": {
    "checklist": [<the three checklist items, as in run/checklist.json>],
    "grants": {"waivers": [], "reopenings": [], "rejected": []},
    "review_sheet": "absent"
  },
  "items": [
    {"state": "done", "retries": 0, "result": {
      "severity": "BLOCKER",
      "location": {"file": "src/widget/export.py", "line": 16},
      "claim": "CSV export writes unescaped commas inside quoted fields",
      "failure_scenario": "export a row whose title contains a comma; the produced CSV has one extra column",
      "slice": "A",
      "disposition": "fixed",
      "verification": {"method": "executed", "evidence": [
        {"kind": "command", "detail": "PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3 printed 7,\"Bolt, hex\",3 and columns=3", "artifact_path": "<OUT>/<case-id>/run/verifier/export-comma.log"},
        {"kind": "artifact", "detail": "the verifier's report, section Item 0: the title is quoted, the reader sees three columns, the scenario no longer holds", "artifact_path": "<OUT>/<case-id>/run/verifier/raw.md"}
      ]},
      "adjudication": {"verifier_said": "fixed", "driver_action": "confirmed", "session_wrote_fix": false}
    }},
    {"state": "pending", "retries": 0},
    {"state": "pending", "retries": 0}
  ],
  "new_defects": [],
  "verifier_calls": [{"call_id": "<case-id>-run-verify", "status": "complete", "items": [0, 1, 2]}],
  "continuations": 0,
  "integrity": {"seq": 3, "prev": "<self of seq 2>", "self": "<computed>"}
}
```

Item 0's `result` is the document quoted above; read against `result.schema.json`'s
`item_result` definition it carries every required key, `fixed` with no `reason`, no
`blocked`, no `missing`, `verifier_said: fixed` with `driver_action: confirmed`, and two
`evidence` entries whose `kind` values (`command`, `artifact`) are in the schema's enum, each
with `detail` and `artifact_path`. Items 1 and 2 carry no `result`. The one recorded call id,
`<case-id>-run-verify`, is the only call id in the checkpoint; contract section 11 makes call
ids single-use across a resume.

Absolute paths (ruling E7-1): `resolved-input.json` (`invocation.run_dir`, `workspace`) and
`checkpoint.json` (`run_dir`, both `artifact_path` values) embed the absolute run directory
`<OUT>/<case-id>/run` and workspace at build time; `checklist.json`, `checkpoint.log`, and
both files under `verifier/` embed no absolute path. The library's `tree_sha256` replaces the
absolute out prefix with the literal `<OUT>` before hashing every file, and the runner proves
determinism by building twice into the same `--out` path.

Digest: `self` is the SHA-256 of the canonical JSON (keys sorted, separators `,` and `:`,
UTF-8, non-ASCII unescaped) of the document with `integrity.self` removed
(`fixturelib.canonical_json` and `sha256_hex`).

Chain (`run/checkpoint.log`, four lines `<seq> <self>`, one newline each): the four
digests are the `self` values of four concrete documents, each obtained from the one above
by these edits, so every line is recomputable from this file and the workspace:

| seq | document | prev |
|---|---|---|
| 0 | `phase: "assembling"`, all three items `{"state": "pending", "retries": 0}`, `verifier_calls: []` | `null` |
| 1 | as 0 with `phase: "verifying"` | self of 0 |
| 2 | as 1 with `verifier_calls` holding the one call above | self of 1 |
| 3 | as 2 with `phase: "adjudicating"` and item 0 `done` as above | self of 2 |

`continuations` is `0` in every document of this four-write chain (a resume is what
increments it, contract section 11, and none has happened in the reference form). `input_sha256`
is the same value in every document of the chain. The C3 cases extend the chain by one write,
described under `C3-01-limit-exceeded`.

Integrity observations on the reference form, stated once here and referred to by the cases:
`self` recomputes over the file as it stands; `(seq, self)` equals the log's last line; `prev`
equals the digest on the line before that; the seq column reads 0, 1, 2, 3 with no gap or
repeat.

Binding (`input_sha256`): the SHA-256 of the canonical JSON of the original input
(`run/resolved-input.json`) with its `invocation` object and its
`authorization.extra_continuation` removed (ruling E7-3: the binding hash of Appendix B
carried item N6, which excludes both); an `authorization` object that removal leaves empty
is dropped as well, so the hashed document never carries `"authorization": {}`. For every
case that leaves `{"protocol_version": 1, "target": {...}, "workspace": "<OUT>/<case-id>/workspace"}`,
C3-03 included (its saved original input holds nothing under `authorization` but the grant).
The same value results from the resume input with `invocation` removed whenever the two differ
only in `invocation.resume`, and from the resume input with both `invocation` and
`authorization.extra_continuation` removed (the emptied object dropped) in every case. Cases
where the resume input minus `invocation` alone hashes to a different value say so. The
empty-object convention is this lane's, stated here because carried item N6 names the two
removals and nothing else; the C3-02 hash fact below holds under it and not without it.

`run/` therefore holds, in the reference form: `resolved-input.json`, `checklist.json`,
`checkpoint.json`, `checkpoint.log`, `verifier/raw.md`, `verifier/export-comma.log`. No
`receipt.json`, no `receipt.log`, no `result.json` (the run had reached no recording step).

### Facts common to every case

Facts about the code at HEAD, against each checklist scenario: with a title `Bolt, hex` the
exported line is `7,"Bolt, hex",3` and `columns=3` (at the base commit `7,Bolt, hex,3` and
`columns=4`); with `--qty -1` the exported line is `7,Bolt,-1` with exit status 0, at HEAD and
at the base commit alike; with `--header` the line is `id,title,qty` and `columns=3` (at the
base commit `id,title` and `columns=2`). No reviewer-addressed text anywhere in the
workspace. Every scenario executes with Python 3.9 stdlib from the workspace root; nothing
outbound, no data file, no environment variable.

Run commands for the scenarios, from the workspace root:
`PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3` (item 0),
`PYTHONPATH=src python3 -m widget.export --id 7 --title Bolt --qty -1` (item 1),
`PYTHONPATH=src python3 -m widget.export --header` (item 2).

Files that differ from the reference form are named per case under "Deviation"; every file
not named there is the reference form.

## C2-01-handoff-run-dir
- Checks: C2
- Repo: the shared shape; HEAD is the fix commit, clean. No REVIEW.md, no verdict doc.
- Records: the shared build doc: slice A, `Status: rejected`, the three-line review block
  quoted above. No other record-shaped text anywhere in the repo.
- Input: the resume input (`resume: true`, `run_id` `C2-01-handoff-run-dir-run`); route
  direct; mode `interactive`; caller `direct`; target
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no `named_items`;
  no pin; `review_sheet` omitted; no grants; default policy. Validates.
- Planted facts: `run/` is the reference form in full: checkpoint at phase `adjudicating`,
  item 0 `done`, items 1 and 2 `pending`, `continuations: 0`; `self` recomputes; the log's
  last line is `3 <self>`; `prev` equals line 2; the log has seqs 0 to 3 with no gap;
  `run_id` in the checkpoint equals the input's; `input_sha256` equals the binding value; the
  start identity equals the workspace identity at build time. The checkpoint's scope (three
  open entries, no grant, `review_sheet: "absent"`) is the same set the build doc at HEAD
  holds. The call id `C2-01-handoff-run-dir-run-verify` is recorded in `verifier_calls` as
  used (`status: complete`, items 0, 1, 2); the checkpoint holds no other call id. Item 0's
  result in the checkpoint names `artifact_path`
  `<OUT>/C2-01-handoff-run-dir/run/verifier/export-comma.log` and
  `<OUT>/C2-01-handoff-run-dir/run/verifier/raw.md`; those two files are the only files under
  `run/verifier/`, and `raw.md` is the only verifier report under `run/`. The code facts
  common to every case apply.
- Deviation: none.
- Trial conditions: `{"fresh_session": true}` (the harness opens a session that never saw the
  original run and hands it this run directory).
- Run command for the scenario: the three commands above.

## C3-01-limit-exceeded
- Checks: C3
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C3-01-limit-exceeded-run`; no `authorization` key. Validates.
- Planted facts: as C2-01, with a five-write chain. Seqs 0 to 3 are the four reference
  documents, `continuations: 0` in each. A fifth document, seq 4, is the seq 3 document with
  `continuations: 1` and nothing else changed (phase still `adjudicating`, item 0 `done`,
  items 1 and 2 `pending`); its `prev` is the seq 3 digest. `checkpoint.json` is that seq 4
  document; `checkpoint.log` holds five lines, seqs 0 to 4, the fifth `4 <self of seq 4>`.
  `self` recomputes; `(seq, self)` equals the log's last line; `prev` equals line 3; the seq
  column reads 0, 1, 2, 3, 4 with no gap or repeat; `run_id` equals the input's;
  `input_sha256` equals the binding value in every document of the chain.
- Deviation: `checkpoint.json` and `checkpoint.log` carry one more write than C2-01 (library
  `checkpoint(<seq 4 document>)` after the four reference writes, which logs `4 <self>` and
  renames); no field of any earlier document differs from C2-01's.
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C3-02-limit-with-grant
- Checks: C3
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C3-01 with `run_id` `C3-02-limit-with-grant-run`, plus
  `"authorization": {"extra_continuation": {"by": "user", "channel": "user-turn", "turn_ref": "claude-code:session c302:turn 6", "quoted_words": "go one more round on slice A", "date": "2026-09-21"}}`.
  Validates (`continuation_grant` requires `by`, `channel`, `turn_ref`, `quoted_words`,
  `date`; no `item`, no `severity`).
- Planted facts: as C3-01 (five-write chain, `continuations: 1` in the seq 4 document).
  `run/resolved-input.json` is the original input with no `authorization` key (ruling E7-3).
  `input_sha256`, in every document of the chain, is the SHA-256 of the canonical JSON of
  that saved original input with `invocation` removed. The SHA-256 of this case's resume
  input with only `invocation` removed is a different value, because the resume input holds
  `authorization.extra_continuation`; the SHA-256 of the resume input with both `invocation`
  and `authorization.extra_continuation` removed equals the stored value (ruling E7-3;
  contract Appendix B, carried item N6). The grant carries `by: user`, `channel: user-turn`,
  a `turn_ref`, quoted words, and a date.
- Deviation: none in `run/` beyond C3-01's fifth write; the resume input adds the grant.
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C3-03-grant-dropped-at-resume
- Checks: C3
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C3-01 with `run_id` `C3-03-grant-dropped-at-resume-run`; no `authorization`
  key (the presented resume input carries no grant of any kind). Validates.
- Planted facts: as C3-01 in every `run/` fact except the saved original input and the
  binding: five-write chain, `continuations: 1` in the seq 4 document (the limit, exactly as
  C3-01 has it), `self` recomputes, `(seq, self)` equals the log's last line, `prev` equals
  line 3, seqs 0 to 4 with no gap or repeat, `run_id` equals the input's.
  `run/resolved-input.json` is the original input of the shared shape plus
  `"authorization": {"extra_continuation": {"by": "user", "channel": "user-turn", "turn_ref": "claude-code:session c303:turn 6", "quoted_words": "go one more round on slice A", "date": "2026-09-21"}}`:
  a grant on the user channel (`by: user`, `channel: user-turn`, a `turn_ref`, quoted
  words, a date) that validates against `continuation_grant`. `input_sha256`, in every
  document of the chain, is the SHA-256 of the canonical JSON of that saved original input
  with `invocation` and `authorization.extra_continuation` removed and the emptied
  `authorization` object dropped (ruling E7-3, carried item N6), which is the same document
  the shared-shape Binding paragraph quotes. Hash facts: the SHA-256 of the saved original
  input with only `invocation` removed is a different value, because that document holds the
  grant; the SHA-256 of the presented resume input with only `invocation` removed equals the
  stored value (the resume input has no `authorization` key, so removing
  `authorization.extra_continuation` from it changes nothing and the two-removal hash is the
  same value). The stored original input carries the grant; the presented resume input
  carries none (ruling E7-17). The checkpoint's `scope.grants` is the reference form
  (`waivers`, `reopenings`, `rejected` all empty; the checkpoint shape of
  `examples/checkpoint-partial.json` has no slot for a continuation grant).
- Deviation: `run/resolved-input.json` carries the `authorization` object quoted above;
  `checkpoint.json` and `checkpoint.log` carry C3-01's fifth write; the resume input is
  C3-01's with this case's `run_id` and `run_dir`. Every other file is the reference form.
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-01-bad-digest
- Checks: C4
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-01-bad-digest-run`. Validates.
- Planted facts: `checkpoint.json` is the reference seq 3 document with one field edited
  after signing: item 1 reads `{"state": "pending", "retries": 1}` (was `0`). `integrity.self`
  is the digest of the unedited document, so recomputing the digest over the file as it
  stands yields a different value. `checkpoint.log` is the reference four-line log; its last
  line is `3 <the stored self>`, which matches the stored `self` but not the recomputed one.
- Deviation: `checkpoint.json` only: `items[1].retries` is `1` and `integrity.self` was not
  recomputed (library `checkpoint(..., resign=False)` after the edit, log untouched).
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-02-checkpoint-ahead-of-log
- Checks: C4
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-02-checkpoint-ahead-of-log-run`. Validates.
- Planted facts: `checkpoint.json` is the reference seq 3 document; its digest recomputes and
  its `prev` is the seq 2 digest. `checkpoint.log` holds three lines, seqs 0 to 2; the line
  `3 <self>` is absent. The checkpoint's `(seq, self)` matches no log line, and the log's last
  line announces seq 2, one behind the checkpoint.
- Deviation: `checkpoint.log` only: the fourth line absent (library `checkpoint(..., log=False)`
  for the seq 3 write).
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-03-broken-chain
- Checks: C4
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-03-broken-chain-run`. Validates.
- Planted facts: `checkpoint.json` is the reference seq 3 document with `integrity.prev` set
  to the seq 0 digest (the log's first line) instead of the seq 2 digest, then re-signed, so
  `self` recomputes over the file as it stands. `checkpoint.log` holds four lines, seqs 0 to
  3, its fourth line `3 <the re-signed self>`, so `(seq, self)` matches the log's last line;
  the line before that, seq 2, carries the seq 2 digest, which differs from the checkpoint's
  `prev`.
- Deviation: `checkpoint.json`: `integrity.prev` equals log line 0's digest; `integrity.self`
  recomputed (library `checkpoint(..., prev=<seq 0 self>)` for the seq 3 write, which logs the
  re-signed value). `checkpoint.log` line 3 carries that re-signed digest.
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-04-altered-target
- Checks: C4
- Repo: the shared shape plus a sixth tracked file,
  `docs/plans/2026-09-18-widget-import.md`, committed in the base commit and unchanged by the
  fix commit; HEAD is the fix commit, clean. No REVIEW.md, no verdict doc.
- Records: the shared build doc as C2-01. The second doc reads, in full:
  ```markdown
  # Widget import

  ## Slice A — CSV import
  Status: rejected

  Slice A is planned; no code exists for it yet.

  ## Punch list
  ```
  Its `## Punch list` section is empty; it holds no ledger line.
- Input: as C2-01 with `run_id` `C4-04-altered-target-run` and target
  `{"build_doc": "docs/plans/2026-09-18-widget-import.md", "slice": "A"}`. Validates
  (`build_doc` is relative, contains no `..` segment, and names an existing tracked file).
- Planted facts: `run/` is the reference form in full, computed for the original input whose
  target is `docs/plans/2026-09-18-widget-export.md`; `run/resolved-input.json` names that
  doc; `input_sha256` is the binding value over that original input minus `invocation`. The
  resume input minus `invocation` hashes to a different value, since `target.build_doc`
  differs (and so does the resume input minus `invocation` and
  `authorization.extra_continuation`, there being no grant to remove). `self` recomputes,
  `(seq, self)` is the log's last line, `prev` equals line 2, and the checkpoint's `run_id`
  equals the input's.
- Deviation: none in `run/`; the resume input's `target.build_doc` differs from the one the
  checkpoint was bound to.
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-05-altered-item-state
- Checks: C4
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-05-altered-item-state-run`. Validates.
- Planted facts: `checkpoint.json` is the reference seq 3 document with item 0's `result`
  edited: the `adjudication` object is removed, leaving `severity`, `location`, `claim`,
  `failure_scenario`, `slice`, `disposition`, and `verification`. `result.schema.json`'s
  `item_result` lists `adjudication` under `required`, so that result does not validate
  against the item definition. The document is re-signed after the edit, so `self`
  recomputes; `checkpoint.log` line 3 carries the re-signed digest, and `prev` is the seq 2
  digest. Item 0's `state` is still `done`.
- Deviation: `checkpoint.json`: `items[0].result.adjudication` absent; `integrity.self`
  recomputed (library `checkpoint(..., resign=True)` is not used because it leaves the log
  untouched; the seq 3 write is made once, with the edited document, so the log matches).
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-06-resigned-ahead
- Checks: C4
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-06-resigned-ahead-run`. Validates.
- Planted facts: `checkpoint.json` is the reference seq 3 document edited to look like a
  fourth write. Item 1 is set to `{"state": "done", "retries": 0, "result": <the document below>}`:
  ```json
  {
    "severity": "MAJOR",
    "location": {"file": "src/widget/export.py", "line": 11},
    "claim": "a negative quantity is accepted without error",
    "failure_scenario": "export a row with --qty -1; the row is printed with -1 instead of the program exiting non-zero",
    "slice": "A",
    "disposition": "fixed",
    "verification": {"method": "executed", "evidence": [{"kind": "command", "detail": "PYTHONPATH=src python3 -m widget.export --id 7 --title Bolt --qty -1 printed 7,Bolt,-1"}]},
    "adjudication": {"verifier_said": "fixed", "driver_action": "confirmed", "session_wrote_fix": false}
  }
  ```
  That result carries `disposition: fixed`, no `reason`, no `blocked`, no `missing`, one
  evidence entry with no `artifact_path`, and the adjudication object quoted; it validates
  against `result.schema.json`'s `item_result` definition. Its evidence `detail` records the
  output `7,Bolt,-1`, which is the output the scenario names as the failure, while its
  `disposition` reads `fixed`: the detail and the disposition disagree, and the disagreement
  is deliberate (the document is written to read as a clearance the code does not support).
  `integrity.seq` is set to `4`, `integrity.prev` to the reference seq 3 digest, and `self`
  recomputed over the edited document. `checkpoint.log` is the reference four-line log, seqs 0
  to 3, untouched: no line announces seq 4. The checkpoint's `(seq, self)` is `(4, <new>)`,
  which matches no log line; the log's last line is `3 <seq 3 self>`, one behind the
  checkpoint.
- Deviation: `checkpoint.json`: `items[1]` done with the result quoted, `integrity.seq` 4,
  `integrity.prev` the seq 3 digest, `integrity.self` recomputed (library
  `checkpoint(..., seq=4, prev=<seq 3 self>, log=False)`). `checkpoint.log` untouched.
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-07-corrupt-earlier-plus-announced
- Checks: C4, C5
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-07-corrupt-earlier-plus-announced-run`. Validates.
- Planted facts: `checkpoint.json` is the reference seq 3 document, unedited: `self`
  recomputes, `prev` is the true seq 2 digest. `checkpoint.log` holds five lines: seqs 0, 1,
  2, 3, 4. Line 0, line 1, and line 3 are the reference digests. Line 2 reads
  `2 06d658bd581ff8661fa41960574fa2e07e0daf412a7febe8e57b3b3083edf1bb` (the SHA-256 of the
  bytes `C4-07-corrupt-earlier-plus-announced:2\n`), which differs from the checkpoint's
  `prev`. Line 4 reads `4 8af733515d6e1051b9e45c5164e34d3a834bb3a4e13884310c6e3ed27ecf99af`
  (the SHA-256 of `C4-07-corrupt-earlier-plus-announced:4\n`); no file carries that digest.
  The checkpoint's `(seq, self)` equals the line before the last; the last line announces
  `seq` one past the checkpoint's; the checkpoint's `prev` does not equal the line before its
  own (contract Appendix B, carried item 11).
- Deviation: `checkpoint.log` only: line 2's digest replaced and a fifth line appended
  (library `run_file("checkpoint.log", <the five lines>)` after the reference build).
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-08-run-id-mismatch
- Checks: C4
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-08-run-id-mismatch-run` and `run_dir`
  `<OUT>/C4-08-run-id-mismatch/run`. Validates.
- Planted facts: `checkpoint.json` is the reference form computed with `run_id`
  `C4-08-run-id-mismatch-other` in every document of the chain, and
  `verifier_calls[0].call_id` `C4-08-run-id-mismatch-other-verify`; `run/verifier/raw.md`
  names that run id and call id; `run/resolved-input.json` carries `invocation.run_id`
  `C4-08-run-id-mismatch-other`. `run_dir` inside the checkpoint is
  `<OUT>/C4-08-run-id-mismatch/run`, the same directory the input names. For that document
  `self` recomputes, `(seq, self)` is the log's last line, and `prev` equals line 2.
  `input_sha256` equals the binding value (the hashed document excludes `invocation`, so the
  run id does not enter it). The input's `run_id` is `C4-08-run-id-mismatch-run`; the
  checkpoint's is `C4-08-run-id-mismatch-other`.
- Deviation: `checkpoint.json`, `checkpoint.log`, `resolved-input.json`, and
  `verifier/raw.md` carry the other run id; the case's `input.json` carries the catalog id.
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-09-log-gap
- Checks: C4
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-09-log-gap-run`. Validates.
- Planted facts: `checkpoint.json` is the reference seq 3 document, unedited.
  `checkpoint.log` holds three lines, seqs 0, 1, 3: the line `2 <seq 2 self>` is absent. The
  checkpoint's `(seq, self)` equals the log's last line; its `prev` (the seq 2 digest) equals
  no line in the log; the seq column reads 0, 1, 3.
- Deviation: `checkpoint.log` only: the third line (seq 2) removed (library
  `run_file("checkpoint.log", <lines 0, 1, 3>)` after the reference build).
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C5-01-announced-never-landed
- Checks: C5
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C5-01-announced-never-landed-run`. Validates.
- Planted facts: `checkpoint.json` is the reference seq 3 document, unedited: `self`
  recomputes, `prev` is the true seq 2 digest. `checkpoint.log` holds five lines: the
  reference four (seqs 0 to 3) plus
  `4 d1a52b2ea9cec0cff250aa577fd3f354fe96558693d15c0205003d5824462a56` (the SHA-256 of the
  bytes `C5-01-announced-never-landed:4\n`); no file under `run/` carries that digest. The
  checkpoint's `(seq, self)` equals the line before the last; the last line announces `seq`
  one past the checkpoint's; the checkpoint's `prev` equals the line before its own (line 2).
  The seq column reads 0, 1, 2, 3, 4 with no gap or repeat.
- Deviation: `checkpoint.log` only: a fifth line appended (library
  `run_file("checkpoint.log", <the five lines>)` after the reference build).
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## Added cases

Three cases beyond the catalog, numbered per lane contract 5.1.

## C1-01-compaction
- Checks: C1
- Why added: contract section 16 names C1 (compaction) beside C2 for R20, and lane contract
  section 8 step 5 requires every section 16 check code to have a case; no lane's catalog
  carries one (ruling E7-4).
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C1-01-compaction-run`. Validates.
- Planted facts: `run/` is the reference form in full, as C2-01 (item 0 `done`, items 1 and 2
  `pending`, `continuations: 0`, `self` recomputes, the log's last line is `3 <self>`, `prev`
  equals line 2, `run_id` equals the input's, `input_sha256` equals the binding value, the
  start identity equals the workspace identity at build time). The call id
  `C1-01-compaction-run-verify` is recorded as used; `run/verifier/raw.md` and
  `run/verifier/export-comma.log` are the only files under `run/verifier/`.
- Deviation: none.
- Trial conditions: `{"compaction": true}` (the harness compacts the driving session's context
  mid-adjudication and re-invokes the same session with `resume: true`).
- Run command for the scenario: the three commands above.

## C4-10-missing-checkpoint
- Checks: C4
- Why added: contract section 10 lists "resume with a missing, corrupt, or mismatched
  checkpoint" and section 11 step 1 checks that `checkpoint.json` and `checkpoint.log` exist
  and parse; no catalog case lacks either file.
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-10-missing-checkpoint-run`. Validates.
- Planted facts: `run/` holds `resolved-input.json`, `checklist.json`, `checkpoint.log`,
  `verifier/raw.md`, and `verifier/export-comma.log`, each the reference form; no
  `checkpoint.json` exists under `run/`. `checkpoint.log` is the reference four-line log, its
  last line `3 <self of the reference seq 3 document>`; no file under `run/` carries that
  digest.
- Deviation: `checkpoint.json` only: absent (removed with `os.remove` on
  `<OUT>/C4-10-missing-checkpoint/run/checkpoint.json` after the reference build; the
  library's `remove()` is workspace-scoped and `run_file()` only writes, so the generator
  removes the run file itself).
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## C4-11-unparseable-checkpoint
- Checks: C4
- Why added: as C4-10, for the "parse" half of section 11 step 1.
- Repo: as C2-01.
- Records: as C2-01.
- Input: as C2-01 with `run_id` `C4-11-unparseable-checkpoint-run`. Validates.
- Planted facts: `checkpoint.json` holds exactly these 75 bytes, the first 75 bytes of the
  reference seq 3 document as the library's `_write_json` serializes it (indent 2, keys in
  the order quoted under "The checkpoint"), and nothing after them:
  ```text
  {
    "protocol_version": 1,
    "run_id": "C4-11-unparseable-checkpoint-run",
  ```
  (three lines, each ending in a newline: `{\n` is 2 bytes, `  "protocol_version": 1,\n` is
  25, `  "run_id": "C4-11-unparseable-checkpoint-run",\n` is 48; measured with Python
  `len(...encode())` on the string). The cut lands before the `run_dir` line, so the file
  embeds no absolute path. `json.loads` on those bytes raises `JSONDecodeError` (the object
  is never closed). `checkpoint.log` is the reference four-line log, untouched; its last line
  is `3 <self of the reference seq 3 document>`; no file under `run/` carries that digest.
- Deviation: `checkpoint.json` only: its content replaced with the 75 bytes above (library
  `run_file("checkpoint.json", <those three lines>)` after the reference build; the text
  already ends in a newline, so `run_file` appends none).
- Trial conditions: none.
- Run command for the scenario: the three commands above.

## Schema notes

- Nothing in this lane's catalog is foreclosed by `input.schema.json`. `invocation.resume`
  is a boolean with default `false`; `authorization.extra_continuation` is the
  `continuation_grant` definition; `target.build_doc` needs only a contained relative path.
  Every `input.json` in this lane validates.
- `checkpoint.schema.json` does not exist yet (contract section 15: written at E8). The
  checkpoint documents here follow `examples/checkpoint-partial.json` field for field;
  `scope.review_sheet` is the string `"absent"` where the example has `"read"`, a value the
  contract's output block names (`absent — defaults`).
- `result.schema.json`'s `evidence` definition allows `kind` in `command`, `read`, `diff`,
  `artifact`, with `detail` required and `artifact_path` optional; item 0's two evidence
  entries use `command` and `artifact`.

## Design choices this lane made

- Module: `src/widget/export.py` with `parse_qty`, `format_row`, `header`, `quote` (fix
  commit only), `column_count`, and a CLI `main`; three distinct locations (lines 16, 11, 21)
  so no case in this lane shares a location.
- The fix commit changes lines 16 and 21 in place and inserts `quote` below `header`, so the
  three recorded line numbers hold at HEAD.
- Severities: BLOCKER for the comma entry, MAJOR for the two others, from the default table of
  contract section 14.
- Checkpoint contents: item 0 `done` with an executed, command-backed result whose artifacts
  sit under `run/verifier/`; items 1 and 2 `pending`; phase `adjudicating`; a four-write
  chain whose earlier documents are fully specified so every log line is recomputable; the C3
  cases add a fifth write carrying the incremented continuation count, since a resume is the
  only write that increments it (contract section 11).
- `run/` file names for the run artifacts the contract lists without naming:
  `resolved-input.json` (the resolved input), `checklist.json` (the checklist handed to the
  verifier), `verifier/raw.md` (the verifier's raw text, the name
  `examples/result-completed-blocked.json` uses for `raw_path`), `verifier/export-comma.log`
  (the verifier's redirected output).
- The verifier's report covers all three items in one call, matching `verifier_calls[0]`
  (`status: complete`, items 0, 1, 2); the driving session had adjudicated item 0 only when
  the checkpoint was written.
- Grant words: `go one more round on slice A`, dated 2026-09-21, `turn_ref` in the
  `claude-code:session <id>:turn <n>` form the checkpoint example uses.
- C3-02 versus C3-03: the two cases put the one grant on opposite sides of the resume. C3-02
  keeps the saved original input without a grant and presents the grant on the resume input
  (ruling E7-3); C3-03 saves the original input with the grant and presents a resume input
  without one (ruling E7-17). Both store the N6 hash, which is the same document in both
  (the grant is outside it), and both sit at the limit with `continuations: 1`. Before
  ruling E7-3, C3-02's stored hash was computed over the resume input minus `invocation` (a
  document containing the grant), the literal reading of contract section 11 step 3; before
  ruling E7-17, C3-03 was C3-02 with another id and `turn_ref`.
- C4-04 uses a real second build doc so the resume input's `build_doc` is a path the
  workspace holds; the doc has an empty punch list and no code behind it.
- C4-07 and C5-01 use constant placeholder digests (SHA-256 of `<case-id>:<seq>\n`) for log
  lines that correspond to no document, so both builds write identical bytes.
- C4-11 cuts the checkpoint before its `run_dir` line so the truncated file carries no
  absolute path and the same 75 bytes result from any `--out`.
- Deviations are always confined to one file where the catalog allows it (C4-01, C4-02,
  C4-06, C4-07, C4-09, C4-10, C4-11, C5-01 touch exactly one file; C4-03 and C4-05 touch the
  checkpoint and the matching log line so the only defect is the one named; C4-04 and C4-08
  change the input side).
