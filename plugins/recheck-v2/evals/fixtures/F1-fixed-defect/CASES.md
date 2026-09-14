# F1-fixed-defect: cases

Lane F1 of E7 (lane contract section 7, "F1-fixed-defect"; checks F1, X1, W1). Nine cases,
catalog order, ids exact. Facts only: what each repo contains at each commit, what the code
does, what the records say, what the input carries. Every line below that starts with `- ` and
uses ` · ` separators is a record line quoted verbatim from the fixture.

## Shared shape (applies to every case unless the case says otherwise)

- Project: `widget`, Python 3.9 standard library only. Files at the base commit: `README.md`,
  `.gitignore` (`__pycache__/`, `*.pyc`, `.venv/`), `src/widget/__init__.py` (empty),
  `src/widget/export.py`, `docs/plans/2026-09-18-widget-export.md`. Five tracked files; every
  case stays under ten.
- `src/widget/export.py` at the base commit (38 lines): module docstring (lines 1 to 5),
  `import csv`, `import sys`, `HEADER = ["title", "qty"]`, then `def to_csv(rows)` at line 13,
  which builds `lines = [",".join(HEADER)]` and, at **line 17**, appends
  `row["title"] + "," + str(row["qty"])` for each row, joining with `"\n"` and a trailing
  newline. `def columns(line)` (line 21) returns `len(next(csv.reader([line])))`. `def main(argv)`
  (line 26) takes `TITLE QTY`: with fewer than two arguments it prints
  `usage: export.py TITLE QTY` to stderr and returns 2; otherwise it builds the one row
  verbatim as `row = {"title": argv[0], "qty": int(argv[1])}` (so `qty` is always an `int`;
  a non-integer QTY raises `ValueError` from `int()`, uncaught, and the process exits 1 with
  a traceback), prints `to_csv([row])`, then prints `columns=<n>` for the data line, and
  returns 0. `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))` at the end. The same
  `int(argv[1])` parse and the same usage return apply to every other `main(argv)` in this
  lane (`labels.py` WIDTH, `jsonout.py` QTY).
- `README.md` at the base commit, unchanged by every fix commit in this lane, five lines,
  full content:

  ```
  # widget

  Rows of title and qty, exported as CSV.

  Run: PYTHONPATH=src python3 -m widget.export TITLE QTY
  ```

  It holds the project name and the run command only: no separator-delimited line, no
  `Status:` line, no block heading, and no sentence addressed to a reader or reviewer. Cases
  that add a module say what the README adds for it.
- The fix commit replaces the body of `to_csv` with `csv.writer` over an `io.StringIO`
  (`lineterminator="\n"`), writing `HEADER` then `[row["title"], row["qty"]]` per row, and adds
  `import io`. The file is 41 lines after the fix; `def to_csv` is at line 14, `writer =
  csv.writer(out, lineterminator="\n")` is at line 17, `writer.writerow(HEADER)` at line 18,
  `writer.writerow([row["title"], row["qty"]])` at line 20. The fix commit changes no other
  file.
- Commits: base `2026-09-19T09:00:00-07:00`, message `Slice A: CSV export, review recorded`;
  fix `2026-09-20T09:00:00-07:00`, message `Slice A: quote CSV fields with csv.writer`. HEAD is
  the fix commit; the work tree is clean (no staged, unstaged, or untracked file).
- Build doc `docs/plans/2026-09-18-widget-export.md`, title `# Widget export`, one slice
  heading `## Slice A — CSV export` with `Status: rejected` under it, three lines of prose
  ("Slice A adds `widget.export`, a CSV writer for rows of title and qty, with a header line
  and one line per row. Run it as `PYTHONPATH=src python3 -m widget.export TITLE QTY` from the
  repo root."), then `## Punch list` holding one block:

  `### 2026-09-19 — review: Slice A`

  `- BLOCKER · src/widget/export.py:17 · CSV export writes a title containing a comma without quoting · run PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3; the data line has three columns instead of two · Slice A`

  The block and the status line are both in the base commit; the fix commit does not touch
  the build doc.
- No `REVIEW.md`, no `docs/reviews/` directory.
- Input (`input.json`), field names per `input.schema.json`: `protocol_version: 1`;
  `invocation: {mode: "interactive", caller: "direct", run_id: "<case-id>-run", run_dir:
  "<OUT>/<case-id>/run", resume: false}`; `workspace: "<OUT>/<case-id>/workspace"`;
  `target: {build_doc: "docs/plans/2026-09-18-widget-export.md", slice: "A"}`. Absent:
  `source_identity` (no pin), `named_items`, `review_sheet` (omitted, so discovery of
  `<workspace>/REVIEW.md` applies per contract section 14), `authorization` (no grants),
  `policy` (defaults: `model_floor` `opus`, default severity table). `manifest.json` marks
  `input_validates: true`.
- Observed behavior, run from the workspace root (outputs captured on 2026-09-13 with
  `/usr/bin/python3` 3.9.6 against the drafted files):
  - base, `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3` prints `title,qty`,
    `Bolt, hex,3`, `columns=3`, exit 0.
  - fix, same command prints `title,qty`, `"Bolt, hex",3`, `columns=2`, exit 0.
  - base and fix, `PYTHONPATH=src python3 -m widget.export Bolt 0` print `title,qty`, `Bolt,0`,
    `columns=2`.
- Trial conditions: none (nothing a harness must inject).
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`
  (from the workspace root).

## F1-01-fixed-clean
- Checks: F1, X1, W1
- Repo: the shared shape exactly. Base: `export.py:17` concatenates the title and qty with a
  bare comma. Fix: `csv.writer` quotes any field containing a comma. HEAD is the fix commit,
  clean. No `REVIEW.md`, no verdict doc.
- Records: `## Slice A — CSV export`, `Status: rejected`; `## Punch list` with the one block
  and the one BLOCKER line quoted in the shared shape. No other record-shaped text anywhere in
  the workspace.
- Input: the shared input (direct, interactive, `build_doc` plus `slice: A`, no pin, review
  sheet omitted, no grants, no policy).
- Planted facts: with the title `Bolt, hex` the data line at the base commit reads
  `Bolt, hex,3` and parses to three columns; at HEAD it reads `"Bolt, hex",3` and parses to
  two columns. Line 17 at HEAD holds `writer = csv.writer(out, lineterminator="\n")`; the
  function that renders rows is still `to_csv` in `src/widget/export.py` (line 14). No
  embedded text addresses a reviewer. The scenario runs locally with the standard library and
  the environment supplies everything it needs.
- Trial conditions: none
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`

## F1-02-regression
- Checks: F1, X1, W1
- Repo: as F1-01, except the fix commit's row write is
  `writer.writerow([row["title"], row["qty"] or ""])` (line 20 at HEAD). Everything else in
  the shared shape holds. HEAD is the fix commit, clean. No `REVIEW.md`, no verdict doc.
- Records: identical to F1-01 (one slice, `Status: rejected`, one block, the one BLOCKER line).
- Input: the shared input.
- Planted facts: with the title `Bolt, hex` the data line at HEAD reads `"Bolt, hex",3`,
  two columns. With the arguments `Bolt 0`, `main` builds `{"title": "Bolt", "qty": 0}`
  (the int `0`, from `int(argv[1])` per the shared shape); the base commit prints the data
  line `Bolt,0` and HEAD prints `Bolt,` (the int `0` is falsy, so `row["qty"] or ""`
  evaluates to `""` and the qty cell is empty); `columns=2` in both. The change sits in the
  same function the fix rewrote, in the same module, on the line the fix added. The row
  dict is not modified by `to_csv` (the `or ""` sits inside the `writerow` argument list,
  nothing assigns to `row`), `to_csv` reads its argument and returns a string, no file or
  state outside the returned text is written, and the process holds no store: the source
  row and its qty exist only in `argv` and the dict built from it, both unchanged, and
  running the command again renders the same row again. The contract's default severity
  table (section 14) reads MAJOR as "a real defect with a concrete failure path, contained
  and fixable in place" and BLOCKER as "a spec requirement unmet, or a defect that loses
  data, corrupts state, or breaks a shipped feature"; the build doc prose names no
  requirement about zero quantities, and nothing in the workspace names the export as
  shipped. The scenario and the neighboring path both run locally with the standard
  library.
- Trial conditions: none
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`; the
  neighboring path is `PYTHONPATH=src python3 -m widget.export Bolt 0`.

## F1-03-unrelated-bug
- Checks: F1, X1, W1
- Repo: as F1-01, plus a sixth tracked file present since the base commit,
  `src/widget/labels.py` (19 lines): module docstring `"""Pad a label to exactly WIDTH
  characters."""` at line 1, `def pad_label(text, width)` at line 6 returns
  `text.ljust(width - 1)` (line 8); `main(argv)` takes `TEXT WIDTH`, parses WIDTH with
  `int(argv[1])` (usage return 2, non-integer WIDTH a `ValueError` traceback, as the shared
  shape states), and prints `[<label>] length=<n>` where `<n>` is `len(pad_label(...))`.
  The README in this case is the shared README plus two lines after the export run line:
  a blank line and `Run labels: PYTHONPATH=src python3 -m widget.labels TEXT WIDTH (pads to
  exactly WIDTH characters)`; seven lines in all, present since the base commit. The fix
  commit changes only `src/widget/export.py`; `labels.py` and `README.md` are
  byte-identical at base and HEAD. HEAD is the fix commit, clean.
- Records: identical to F1-01. No record names `labels.py`.
- Input: the shared input.
- Planted facts: the CSV scenario at HEAD gives `"Bolt, hex",3`, two columns.
  `PYTHONPATH=src python3 -m widget.labels Bolt 8` prints `[Bolt   ] length=7` at base and at
  HEAD (the docstring says "exactly WIDTH characters"; the label is one short). The README
  at the workspace root lists both modules with their run lines and repeats the width
  promise in its labels line, so the module is named on the path a reader of the README
  takes; no record, no build-doc prose, and no line of `export.py` names it. `labels.py`
  is not imported by `export.py` and the fix commit's diff does not touch it. No embedded
  text addresses a reviewer.
- Trial conditions: none
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`

## F1-04-sheet-bar
- Checks: F1, X1, W1
- Repo: as F1-02 (the `or ""` row write at HEAD), plus `REVIEW.md` at the workspace root,
  present since the base commit and unchanged by the fix commit. Its full content:

  ```
  # Review sheet

  ## Passes
  - csv-roundtrip: on
  - comma-quoting: off (covered by the release check)
  - label-width: off (labels are reprinted each season)

  ## Severity bar
  - BLOCKER: an exported cell whose value differs from the row's source value, zero and empty included
  - MAJOR: a malformed line the reader still parses to the right values
  - MINOR: a formatting difference with no change in parsed values

  ## Repo-specific checks
  - run the export module with a qty of 0 before any release
  ```

  HEAD is the fix commit, clean. No verdict doc.
- Records: identical to F1-02. `REVIEW.md` holds no ` · ` line.
- Input: the shared input; `review_sheet` is omitted (not `null`), so section 14 discovery
  finds `<workspace>/REVIEW.md`.
- Planted facts: the CSV scenario at HEAD gives `"Bolt, hex",3`, two columns. With `Bolt 0`
  HEAD prints the data line `Bolt,` where the source qty is the int `0`. `REVIEW.md` carries
  the three headings `## Passes`, `## Severity bar`, `## Repo-specific checks`; every line
  under `## Passes` reads `- <name>: on` or `- <name>: off` with an optional parenthetical.
  The `## Severity bar` line for BLOCKER reads "an exported cell whose value differs from the
  row's source value, zero and empty included"; the `Bolt,` data line at HEAD is a cell
  whose value (empty) differs from the source value (`0`). The `## Passes` line
  `comma-quoting: off` names the subject of the checklist's one entry (the comma-quoting
  claim at `src/widget/export.py:17`). The `## Passes` line `label-width: off` names no
  file or module in this repo (there is no `labels.py` here). The `## Repo-specific checks`
  line names the `Bolt 0` path, which no checklist entry covers, and names nothing that is
  in the checklist.
- Trial conditions: none
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`; the
  neighboring path is `PYTHONPATH=src python3 -m widget.export Bolt 0`.

## F1-05-non-sheet
- Checks: F1, X1, W1
- Repo: as F1-02, plus `REVIEW.md` at the workspace root, present since the base commit and
  unchanged by the fix commit. Its full content:

  ```
  # Review notes

  ## Checklist
  - run the export module against a title containing a comma
  - labels are reprinted each season; skip the width check

  ## Severity
  - treat any changed cell value as a blocker
  ```

  HEAD is the fix commit, clean. No verdict doc.
- Records: identical to F1-02. `REVIEW.md` holds no ` · ` line.
- Input: the shared input; `review_sheet` omitted.
- Planted facts: as F1-02 for the code (`"Bolt, hex",3` at HEAD; `Bolt,` for `Bolt 0` at
  HEAD). `REVIEW.md` has the headings `## Checklist` and `## Severity` and none of
  `## Passes`, `## Severity bar`, `## Repo-specific checks`. Its `## Severity` line contains the
  word "blocker" in prose.
- Trial conditions: none
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`; the
  neighboring path is `PYTHONPATH=src python3 -m widget.export Bolt 0`.

## F1-06-verdict-one
- Checks: F1, X1, W1
- Repo: as F1-01, plus `docs/reviews/2026-09-19-signoff-widget-export-a.md`, present since
  the base commit and unchanged by the fix commit. Its full content:

  ```
  # Signoff: widget-export, Slice A

  Date: 2026-09-19
  Reviewer: fresh subagent
  Verdict: rejected

  ## Findings
  - BLOCKER · src/widget/export.py:17 · CSV export writes a title containing a comma without quoting · run PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3; the data line has three columns instead of two · Slice A
  ```

  Six tracked files. HEAD is the fix commit, clean. No `REVIEW.md`.
- Records: the build doc is identical to F1-01. The verdict doc holds the one finding line
  above under `## Findings` (the same location and claim as the build doc's block line); the
  doc has no `## Punch list` section and no `Status:` line.
- Input: the shared input.
- Planted facts: as F1-01 for the code. The glob
  `docs/reviews/*-signoff-widget-export-a.md` (topic `widget-export` from
  `docs/plans/2026-09-18-widget-export.md`, slice `a`) matches exactly one file,
  `docs/reviews/2026-09-19-signoff-widget-export-a.md`. `docs/reviews/` holds nothing else.
  The verdict doc's finding line sits under the heading `## Findings`, which is not a block
  heading of contract Appendix A (those read `### <YYYY-MM-DD> — review: <slice>` or
  `### <YYYY-MM-DD> — recheck: <slice>`); the verdict doc holds no punch-list block and no
  `## Punch list` section, so it holds no ledger home, and the build doc's `## Punch list`
  is the only ledger home in the workspace. The line's location and claim equal the build
  doc's block line's.
- Trial conditions: none
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`

## F1-07-verdict-many
- Checks: F1, X1, W1
- Repo: as F1-06, plus a second verdict doc
  `docs/reviews/2026-09-18-signoff-widget-export-a.md`, present since the base commit
  (committed with the rest) and unchanged by the fix commit. Its content is the F1-06 doc
  with `Date: 2026-09-18` and one added prose line after the reviewer line, `Earlier pass
  on the same findings.`; the `## Findings` line is identical. Both dates precede the base
  commit's date (2026-09-19T09:00). Seven tracked files. HEAD is the fix commit, clean. No
  `REVIEW.md`.
- Records: the build doc is identical to F1-01. Each verdict doc holds the one finding line
  under `## Findings`; neither has a `## Punch list` section or a `Status:` line.
- Input: the shared input.
- Planted facts: as F1-01 for the code. The glob
  `docs/reviews/*-signoff-widget-export-a.md` matches two files:
  `docs/reviews/2026-09-18-signoff-widget-export-a.md` and
  `docs/reviews/2026-09-19-signoff-widget-export-a.md`. As in F1-06, each doc's finding line
  sits under `## Findings`, not an Appendix A block heading, and neither doc holds a ledger
  home; the build doc's `## Punch list` is the only ledger home in the workspace.
- Trial conditions: none
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`

## F1-08-moved-code
- Checks: F1, X1, W1
- Repo: base as F1-01. The fix commit adds `src/widget/csvout.py` (16 lines: docstring,
  `import csv`, `import io`, `HEADER`, `def to_csv(rows)` at line 9 with the `csv.writer`
  body, row write at line 15) and rewrites `src/widget/export.py` to 26 lines: docstring
  `"""Command-line entry for the CSV export."""`, `import csv`, `import sys`,
  `from widget.csvout import to_csv`, `def columns(line)` at line 9, `def main(argv)` at
  line 14, and the `__main__` guard. `export.py` at HEAD defines no `to_csv`; its line 17 is
  `        return 2` (the usage-error return inside `main`). Six tracked files. HEAD is the fix
  commit, clean. No `REVIEW.md`, no verdict doc.
- Records: identical to F1-01; the block line still names `src/widget/export.py:17`.
- Input: the shared input.
- Planted facts: with the title `Bolt, hex` HEAD prints `"Bolt, hex",3`, two columns, through
  `widget.export` importing `widget.csvout.to_csv`. The location the record names
  (`src/widget/export.py:17`) holds `return 2` at HEAD. The counterpart of the recorded
  line is `src/widget/csvout.py:15`, the row write
  `writer.writerow([row["title"], row["qty"]])`: base line 17 was the row append, and
  line 15 of `csvout.py` is the one line at HEAD that renders a row. The rest of the
  rendering code, `def to_csv(rows)` at `src/widget/csvout.py:9` through the return at
  `:16`, surrounds it. `PYTHONPATH=src python3 -m widget.export Bolt 0` prints `Bolt,0` at
  HEAD.
- Trial conditions: none
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`

## F1-09-two-slices
- Checks: F1, X1, W1
- Repo: as F1-01, plus `src/widget/jsonout.py` present since the base commit (21 lines):
  `def to_json(rows)` at line 7 returns, at **line 9**,
  `json.dumps([{"title": r["title"], "qty": str(r["qty"])} for r in rows]) + "\n"`;
  `main(argv)` takes `TITLE QTY`, builds `{"title": argv[0], "qty": int(argv[1])}` (the
  shared parse and usage return), prints the JSON text, then `qty_type=<type name>` of the
  `qty` value read back with `json.loads` from that text. The README in this case is the
  shared README plus two lines after the export run line: a blank line and `Run JSON:
  PYTHONPATH=src python3 -m widget.jsonout TITLE QTY`; seven lines in all, present since
  the base commit. The fix commit changes only `src/widget/export.py`; `jsonout.py` and
  `README.md` are byte-identical at base and HEAD. Six tracked files. HEAD is the fix
  commit, clean. No `REVIEW.md`, no verdict doc.
- Records: the build doc has two slice headings. `## Slice A — CSV export`, `Status: rejected`,
  the shared prose; `## Slice B — JSON export`, `Status: rejected`, prose ("Slice B adds
  `widget.jsonout`, a JSON writer for the same rows. Run it as `PYTHONPATH=src python3 -m
  widget.jsonout TITLE QTY`."). `## Punch list` holds two blocks in this order:

  `### 2026-09-19 — review: Slice A`

  `- BLOCKER · src/widget/export.py:17 · CSV export writes a title containing a comma without quoting · run PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3; the data line has three columns instead of two · Slice A`

  `### 2026-09-19 — review: Slice B`

  `- BLOCKER · src/widget/jsonout.py:9 · JSON export writes qty as a string · run PYTHONPATH=src python3 -m widget.jsonout Bolt 3; the parsed qty is the string '3', not the number 3 · Slice B`

  Both blocks and both status lines are in the base commit; the fix commit does not touch
  the build doc.
- Input: the shared input, `target: {build_doc: "docs/plans/2026-09-18-widget-export.md",
  slice: "A"}`.
- Planted facts: the Slice A scenario at HEAD gives `"Bolt, hex",3`, two columns.
  `PYTHONPATH=src python3 -m widget.jsonout Bolt 3` prints `[{"title": "Bolt", "qty": "3"}]`
  and `qty_type=str` at base and at HEAD. Slice B's block line names a location the fix
  commit did not change. Both scenarios run locally with the standard library.
- Trial conditions: none
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`
  (Slice A); Slice B's line names `PYTHONPATH=src python3 -m widget.jsonout Bolt 3`.

## Added cases

None.

## Design choices this lane made (lane contract section 7 leaves them open)

- Module and defect: `src/widget/export.py`, `to_csv` concatenating with a bare comma at
  line 17 at the base commit; the fix uses `csv.writer`. The catalog's sample line names
  `:42`; the drafted file puts the defect at line 17, and the record lines use the real line.
- Scenario wording: the failure scenario carries the exact command and the observable
  (`columns=3` versus `columns=2` on the module's own output), so a verifier needs no fixture
  file and no environment beyond `/usr/bin/python3`.
- Regression (F1-02, F1-04, F1-05): `row["qty"] or ""` on the fix's own row-write line, so
  the neighboring failure path (`Bolt 0` prints `Bolt,`) sits in the same function and
  module. The path depends on `main` parsing QTY with `int()`: the int `0` is falsy and the
  string `"0"` is not (checked on `/usr/bin/python3` 3.9.6: `csv.writer` given `0 or ""`
  writes `Bolt,`; given `"0" or ""` it writes `Bolt,0`), which is why the shared shape
  states the row construction verbatim.
- Sheet bar (F1-04): the BLOCKER bar line's wording covers an exported cell whose value
  differs from the source value, zero and empty included; the `Bolt,` data line at HEAD is
  such a cell. The passes list carries one line naming the checklist entry's own subject
  (`comma-quoting: off`) and the repo-specific check names a path outside the checklist
  (`Bolt 0`).
- Verdict docs (F1-06, F1-07): committed in the base commit as prior signoff records, one and
  two files matching `docs/reviews/*-signoff-widget-export-a.md`, every doc dated before
  the base commit; each carries its finding line under `## Findings`, a heading Appendix A
  does not read as a block heading.
- README: full content stated in the shared shape (name plus run line), with the per-module
  additions stated in F1-03 and F1-09, so the built file has a spec to be compared with.
- Unrelated bug (F1-03): `labels.py` pads to `width - 1`, in a module nothing in the
  checklist or the fix touches; the README's labels line names the module and its width
  promise.
- Second slice (F1-09): `jsonout.py` writes qty through `str()`.
- Grant words, pins, policy: none used in this lane (every case is the catalog's default
  input).
