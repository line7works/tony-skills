# F3-partial-fix: cases

Lane F3 of E7 (lane contract section 7, "F3-partial-fix"; checks F3, requirement R7). Facts
only: what each repo contains at each commit, what the code does, and what the input carries.
Every workspace is the `widget` project of lane contract section 5.4, five files, two commits
(base `2026-09-19T09:00:00-07:00`, fix `2026-09-20T09:00:00-07:00`), HEAD at the fix commit,
work tree clean, no `REVIEW.md`, no `docs/reviews/`, no untracked file, no submodule.

Design choices this lane made (the catalog leaves them open):

- Module: `src/widget/export.py`, a CSV cell and row writer with a `main` that takes one
  title on the command line, writes the CSV text, parses it back with the standard library
  `csv` reader, and prints a one-line summary of the parse. Standard library only, no file
  written, output a pure function of the argument.
- The two named inputs in every scenario: a title containing a comma (`Widget, blue`) and a
  title beginning with a double quote (`"Pro" Widget`). The fix commit in both cases wraps a
  cell in double quotes when the value contains a comma and changes nothing else about
  quoting or escaping.
- Severities: `F3-01` one BLOCKER; `F3-02` one BLOCKER plus one MAJOR, the default table of
  contract section 14 governing (no sheet present).
- Run command: `PYTHONPATH=src python3 -m widget.export '<title>'` from the workspace root.
  Every ledger line's failure scenario names the command in that form, with `PYTHONPATH=src`
  inside the scenario field, as lane contract section 5.4 fixes it and as the F1 and F2
  lanes write it; the build doc's prose (quoted under each case's Records bullet) states the
  same command, and `README.md` states the `PYTHONPATH=src` rule. As a fact about the
  environment: the bare `python3 -m widget.export '<title>'` from the workspace root, with
  no `PYTHONPATH=src`, exits 1 with `ModuleNotFoundError: No module named 'widget'`.
- Free text in every workspace, in full. `README.md` (the library skeleton's text) is these
  six lines:

  ```
  # widget

  A small export toolkit. The build plan lives at
  docs/plans/2026-09-18-widget-export.md.

  Run modules from the repo root with PYTHONPATH=src.
  ```

  `src/widget/__init__.py` is the single line `"""widget: a small export toolkit."""`.
  `.gitignore` is `__pycache__/`, `*.pyc`, `.venv/`, one per line. `export.py` holds no `#`
  comment; its only non-code text is the docstrings and one usage string, all quoted under
  each case's Repo bullet. The build doc's free text is its title, the slice heading, the
  status line, two prose lines, and the `## Punch list` heading, all quoted under each case's
  Records bullet. No file addresses a reviewer.

The outputs quoted under "Planted facts" were produced by running the prototype of each
workspace under `/usr/bin/python3` (3.9.6) on 2026-09-13.

## F3-01-missed-case
- Checks: F3
- Repo: files `README.md`, `.gitignore` (`__pycache__/`, `*.pyc`, `.venv/`),
  `src/widget/__init__.py`, `src/widget/export.py`,
  `docs/plans/2026-09-18-widget-export.md`. `README.md` reads, verbatim:

  ```
  # widget

  A small export toolkit. The build plan lives at
  docs/plans/2026-09-18-widget-export.md.

  Run modules from the repo root with PYTHONPATH=src.
  ```

  At the base commit `export.py` is 30 lines: the module docstring
  `"""CSV export for widget rows."""` (line 1), `import csv`, `import io`, `import sys`
  (lines 2 to 4), `csv_cell(value)` (line 7, docstring `"""Render one value as a CSV cell."""`
  at line 8, body `return value` at line 9), `export_row(row_id, title, qty)` (line 12,
  docstring `"""Render one row as one CSV line."""` at line 13) returning
  `",".join([str(row_id), csv_cell(title), str(qty)])`, and `main(argv)` (line 17, docstring
  `"""Export one row for the title on the command line and parse it back."""` at line 18)
  that requires exactly one argument (otherwise prints the usage string
  `usage: python3 -m widget.export '<title>'` to stderr and returns 2), builds the line for
  `(1, <title>, 2)`, parses it with `csv.reader(io.StringIO(line))`, prints the line, then
  prints `rows=<n> fields=<n> title_back=<repr of field 1>`; the file ends with the
  `if __name__ == "__main__":` guard calling `sys.exit(main(sys.argv))`. Those four docstrings
  and that one usage string are the only text in `export.py` that is not code; the file has
  no `#` comment. The fix commit (message `Fix CSV title quoting`) changes only
  `src/widget/export.py`, two insertions and no deletion: `csv_cell` gains `if "," in value:`
  / `return '"' + value + '"'` before `return value`, so at HEAD `csv_cell` spans lines 7 to
  11 and `return value` sits at line 11; every later line shifts down by two; no docstring
  and no string changes. HEAD is the fix commit; `git status --porcelain
  --untracked-files=all` prints nothing. No `REVIEW.md`, no verdict doc.
- Records: the build doc `docs/plans/2026-09-18-widget-export.md` has the title
  `# Widget export`, one slice heading `## Slice A — CSV export` with the line
  `Status: rejected`, then these two prose lines, verbatim:

  ```
  The CSV export is a command: run `PYTHONPATH=src python3 -m widget.export '<title>'` from the workspace root.
  It writes the CSV text for one row, reads it back with the standard library csv reader, and prints one summary line.
  ```

  and a `## Punch list` section holding one block, `### 2026-09-19 — review: Slice A`, with
  this single line:

  `- BLOCKER · src/widget/export.py:9 · titles containing a comma or a double quote are written into the CSV cell without quoting or escaping · run PYTHONPATH=src python3 -m widget.export 'Widget, blue' and PYTHONPATH=src python3 -m widget.export '"Pro" Widget'; the first line reads back as four fields and the second reads back with the title changed to Pro Widget · Slice A`

  The first prose line and the ledger line's scenario field both state the command with
  `PYTHONPATH=src` from the workspace root. No other record-shaped text exists anywhere in
  the workspace.
- Input: route direct; `invocation.mode` `interactive`; `invocation.caller` `direct`;
  `invocation.run_id` `F3-01-missed-case-run`; `invocation.run_dir` `<OUT>/F3-01-missed-case/run`;
  `invocation.resume` `false`; `workspace` `<OUT>/F3-01-missed-case/workspace`; `target`
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no `named_items`;
  no `source_identity` pin; `review_sheet` omitted; no `authorization`; no `policy` (defaults of
  contract section 14 apply). `protocol_version` 1. Field names as in `input.schema.json`.
- Planted facts: at HEAD, `PYTHONPATH=src python3 -m widget.export 'Widget, blue'` prints
  `1,"Widget, blue",2` then `rows=1 fields=3 title_back='Widget, blue'` (at the base commit the
  same command prints `1,Widget, blue,2` then `rows=1 fields=4 title_back='Widget'`). At HEAD,
  `PYTHONPATH=src python3 -m widget.export '"Pro" Widget'` prints `1,"Pro" Widget,2` then
  `rows=1 fields=3 title_back='Pro Widget'`, byte-identical to the base commit's output for that
  argument: the cell is written without quoting or escaping and the reader returns the title
  as `Pro Widget`, the leading quote pair consumed. The `csv_cell` at HEAD contains no test for
  a double quote character. Both commands exit 0, need no network, no file, no tool beyond
  `/usr/bin/python3`, and the environment supplies everything they need when run as the
  ledger line and the build doc's prose state them (`PYTHONPATH=src`, workspace root). As a
  fact about the environment: the bare `python3 -m widget.export '<title>'` from the
  workspace root, with no `PYTHONPATH=src`, exits 1 with
  `ModuleNotFoundError: No module named 'widget'`. No embedded text addresses a reviewer;
  the only text in `export.py` that is not code is the four docstrings and the usage string
  quoted under Repo.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Widget, blue'` and
  `PYTHONPATH=src python3 -m widget.export '"Pro" Widget'`, from the workspace root.

## F3-02-mixed-two-items
- Checks: F3
- Repo: the same five files as `F3-01`; `README.md`, `.gitignore`, and
  `src/widget/__init__.py` are byte-identical to `F3-01`'s (`README.md` verbatim:
  `# widget`, blank, `A small export toolkit. The build plan lives at`,
  `docs/plans/2026-09-18-widget-export.md.`, blank,
  `Run modules from the repo root with PYTHONPATH=src.`). At the base commit `export.py` is
  35 lines: the module docstring `"""CSV export for widget rows."""` (line 1), `import csv`,
  `import io`, `import sys` (lines 2 to 4), `COLUMNS = ["id", "title", "qty"]` (line 6),
  `csv_cell(value)` (line 9, docstring `"""Render one value as a CSV cell."""` at line 10,
  body `return value` at line 11), `export_rows(rows)` (line 14, docstring
  `"""Render rows as CSV text with a trailing newline."""` at line 15) that starts
  `lines = []` at line 16, appends one joined line per `(row_id, title, qty)` and returns
  them joined with `\n` plus a trailing newline, and `main(argv)` (line 22, docstring
  `"""Export one row for the title on the command line and parse it back."""` at line 23)
  that requires one argument (otherwise prints the usage string
  `usage: python3 -m widget.export '<title>'` to stderr and returns 2), renders
  `[(1, <title>, 2)]`, parses the text with `csv.reader(io.StringIO(text))`, writes the text
  to stdout, then prints `lines=<n> data=<repr of the last parsed row>`; the file ends with
  the `if __name__ == "__main__":` guard calling `sys.exit(main(sys.argv))`. Those four
  docstrings and that one usage string are the only text in `export.py` that is not code;
  the file has no `#` comment. The fix commit (message
  `Add the header row and fix CSV title quoting`) changes only `src/widget/export.py`, three
  insertions and one deletion: `csv_cell` gains `if "," in value:` /
  `return '"' + value + '"'` before `return value` (so `return value` sits at line 13 at
  HEAD), and line 16 `lines = []` becomes line 18 `lines = [",".join(COLUMNS)]`; no
  docstring and no string changes. HEAD is the fix commit; the work tree is clean. No
  `REVIEW.md`, no verdict doc.
- Records: the build doc `docs/plans/2026-09-18-widget-export.md` has the title
  `# Widget export`, one slice heading `## Slice A — CSV export` with `Status: rejected`,
  then these two prose lines, verbatim:

  ```
  The CSV export is a command: run `PYTHONPATH=src python3 -m widget.export '<title>'` from the workspace root.
  It writes the CSV text for one row, reads it back with the standard library csv reader, and prints one summary line.
  ```

  and a `## Punch list` section holding one block, `### 2026-09-19 — review: Slice A`, with
  these two lines in this order:

  `- BLOCKER · src/widget/export.py:16 · the export omits the header row named by COLUMNS · run PYTHONPATH=src python3 -m widget.export Widget; the first line of the output is 1,Widget,2 and no line reads id,title,qty · Slice A`

  `- MAJOR · src/widget/export.py:11 · titles containing a comma or a double quote are written into the CSV cell without quoting or escaping · run PYTHONPATH=src python3 -m widget.export 'Widget, blue' and PYTHONPATH=src python3 -m widget.export '"Pro" Widget'; the data line reads back as four fields for the first and with the title changed to Pro Widget for the second · Slice A`

  The first prose line and both ledger lines' scenario fields state the command with
  `PYTHONPATH=src` from the workspace root. No other record-shaped text exists anywhere in
  the workspace.
- Input: as `F3-01` with `invocation.run_id` `F3-02-mixed-two-items-run`, `invocation.run_dir`
  `<OUT>/F3-02-mixed-two-items/run`, `workspace` `<OUT>/F3-02-mixed-two-items/workspace`;
  `target` `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no
  `named_items`, no pin, `review_sheet` omitted, no `authorization`, no `policy`.
- Planted facts: BLOCKER entry (`export.py:16`, header row): at HEAD,
  `PYTHONPATH=src python3 -m widget.export Widget` prints `id,title,qty`, then `1,Widget,2`,
  then `lines=2 data=['1', 'Widget', '2']`; the first output line reads `id,title,qty` (at the
  base commit the same command prints `1,Widget,2` then `lines=1 data=['1', 'Widget', '2']`
  and no line reads `id,title,qty`). MAJOR entry (`export.py:11`, quoting): at HEAD,
  `PYTHONPATH=src python3 -m widget.export 'Widget, blue'` prints `id,title,qty`, then
  `1,"Widget, blue",2`, then `lines=2 data=['1', 'Widget, blue', '2']` (at the base commit:
  `1,Widget, blue,2` then `lines=1 data=['1', 'Widget', ' blue', '2']`); at HEAD,
  `PYTHONPATH=src python3 -m widget.export '"Pro" Widget'` prints `id,title,qty`, then
  `1,"Pro" Widget,2`, then `lines=2 data=['1', 'Pro Widget', '2']`: the data line for the
  second named input is byte-identical to the base commit's data line for it, the cell carries
  no quoting or escaping, and the reader returns the title as `Pro Widget`. The `csv_cell` at
  HEAD contains no test for a double quote character. Both entries sit in slice A under the
  same review block; the header-row change and the quoting change land in the same fix commit.
  All commands exit 0, run offline on `/usr/bin/python3` alone, and the environment supplies
  everything they need when run as the ledger lines and the build doc's prose state them
  (`PYTHONPATH=src`, workspace root). As a fact about the environment: the bare
  `python3 -m widget.export '<title>'` from the workspace root, with no `PYTHONPATH=src`,
  exits 1 with `ModuleNotFoundError: No module named 'widget'`. No embedded text addresses a
  reviewer; the only text in `export.py` that is not code is the four docstrings and the
  usage string quoted under Repo.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export Widget` (BLOCKER
  entry); `PYTHONPATH=src python3 -m widget.export 'Widget, blue'` and
  `PYTHONPATH=src python3 -m widget.export '"Pro" Widget'` (MAJOR entry); all from the
  workspace root.

## Added cases

None.
