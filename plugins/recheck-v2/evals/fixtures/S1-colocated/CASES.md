# S1-colocated: cases

Lane S1-colocated of recheck-v2 E7 (lane contract section 7, "S1-colocated"; checks S1,
R11, R36). Facts only: what each repo contains at each commit and what the code does. Three
cases, in catalog order. Every record line below is written in the Appendix A grammar with
the separator ` · ` (space, U+00B7, space).

## Shared shape

Every case is the `widget` project of lane contract 5.4, five tracked files at HEAD:

```text
README.md
.gitignore                                  __pycache__/, *.pyc, .venv/
src/widget/__init__.py                      empty
src/widget/export.py                        the module under review
docs/plans/2026-09-18-widget-export.md      the build doc
```

(five paths; `.git/` is not counted; no REVIEW.md, no `docs/reviews/`, no untracked file.)

Commits: base `2026-09-19T09:00:00-07:00` (message `Slice A: CSV export, review recorded`),
fix `2026-09-20T09:00:00-07:00` (message `Slice A: quote CSV fields`). HEAD is the fix
commit; the work tree is clean at HEAD in every case. The build doc is committed in the base
commit and is byte-identical in the fix commit (the fix commit changes `src/widget/export.py`
only).

`src/widget/export.py` at the base commit, 34 lines, the `return` of `format_row` on line 11:

```python
"""CSV export for widget rows."""
import argparse
import csv
import io

FIELDS = ("id", "title", "qty")


def format_row(row):
    """Render one row as a CSV line."""
    return ",".join(str(row.get(k)) for k in FIELDS)


def column_count(line):
    """Count the columns a CSV reader sees in one line."""
    return len(next(csv.reader(io.StringIO(line))))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="widget.export")
    parser.add_argument("--id", default="1")
    parser.add_argument("--title")
    parser.add_argument("--qty", default="2")
    args = parser.parse_args(argv)
    row = {"id": args.id, "qty": args.qty}
    if args.title is not None:
        row["title"] = args.title
    line = format_row(row)
    print(line)
    print("columns=%d" % column_count(line))


if __name__ == "__main__":
    main()
```

What the base code does (measured on the prototype with `/usr/bin/python3` 3.9.6, from the
workspace root):

```text
$ PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3
7,Bolt, hex,3
columns=4
$ PYTHONPATH=src python3 -m widget.export --id 7 --qty 3
7,None,3
columns=3
```

Two fix variants are used across the cases; both keep line 11 as the `return` of
`format_row` and add a `quote` helper directly below it.

Fix variant Q (quote commas), 41 lines; line 11 becomes
`    return ",".join(quote(str(row.get(k))) for k in FIELDS)` and the helper is:

```python
def quote(value):
    """Wrap a value in double quotes when it holds a comma."""
    if "," in value:
        return '"' + value.replace('"', '""') + '"'
    return value
```

Measured on variant Q:

```text
$ PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3
7,"Bolt, hex",3
columns=3
$ PYTHONPATH=src python3 -m widget.export --id 7 --qty 3
7,None,3
columns=3
```

Fix variant QN (quote commas, empty quoted field for a missing value), 44 lines; line 11
becomes `    return ",".join(quote(row.get(k)) for k in FIELDS)` and the helper is:

```python
def quote(value):
    """Render a cell: a missing value is an empty quoted field, a comma forces quotes."""
    if value is None:
        return '""'
    value = str(value)
    if "," in value:
        return '"' + value.replace('"', '""') + '"'
    return value
```

Measured on variant QN:

```text
$ PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3
7,"Bolt, hex",3
columns=3
$ PYTHONPATH=src python3 -m widget.export --id 7 --qty 3
7,"",3
columns=3
```

Build doc skeleton (lane contract 5.4), identical across cases except the ledger lines:

```markdown
# Widget export

## Slice A — CSV export
Status: rejected

Slice A renders widget rows as CSV lines through `widget.export.format_row`. The CLI
`python3 -m widget.export` prints one row and the column count a CSV reader sees.

## Punch list

### 2026-09-19 — review: Slice A
<ledger lines per case>
```

The ledger home is the `## Punch list` section; it holds exactly one block, the review block
dated 2026-09-19. No recheck block, waiver, or reopening line exists in any case. `README.md`
is exactly two lines, ending with one newline and with no blank line between them:

```markdown
# widget
CSV export for widget rows lives in `src/widget/export.py`.
```

It holds no record-shaped text.

Input, common to all three cases (field names from `input.schema.json`):

```json
{
  "protocol_version": 1,
  "invocation": {"mode": "interactive", "caller": "direct", "run_id": "<case-id>-run", "run_dir": "<OUT>/<case-id>/run", "resume": false},
  "workspace": "<OUT>/<case-id>/workspace",
  "target": {"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}
}
```

`named_items`, `source_identity`, `review_sheet`, `authorization`, and `policy` are omitted
(no pin, no grants, default policy; `review_sheet` omitted means auto-discovery of
`<workspace>/REVIEW.md`, which no case contains). `manifest.json` records
`input_validates: true` for every case. `run/` is empty in every case.

## S1-01-two-claims-one-location
- Checks: S1, W3
- Repo: the shared shape. Base commit: `export.py` as listed above. Fix commit: variant Q
  (comma quoting; `str(row.get(k))` still renders a missing title as `None`). HEAD is the fix
  commit, clean. No REVIEW.md, no verdict doc.
- Records: build doc `docs/plans/2026-09-18-widget-export.md`, slice A, `Status: rejected`.
  The review block `### 2026-09-19 — review: Slice A` holds two lines, both at
  `src/widget/export.py:11`, five fields each:
  - `- BLOCKER · src/widget/export.py:11 · CSV export does not quote a field that contains a comma · export a row whose title contains a comma; the produced CSV has one extra column · Slice A`
  - `- MAJOR · src/widget/export.py:11 · a missing title exports as the string None · export a row with no title; the CSV cell reads None instead of an empty quoted field · Slice A`
  No other record-shaped text anywhere in the repo.
- Input: route direct; mode `interactive`; caller `direct`; target
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no `named_items`;
  no pin; `review_sheet` omitted; no grants; default policy. Validates.
- Planted facts: two entries share the join-key location and differ in claim. Against the
  first scenario, at HEAD a title `Bolt, hex` produces `7,"Bolt, hex",3` and `columns=3`; at
  the base commit the same input produces `7,Bolt, hex,3` and `columns=4`. Against the second
  scenario, at HEAD a row with no title produces `7,None,3` (the title cell is the four
  characters `None`); at the base commit it produces the same `7,None,3`. Line 11 at HEAD
  reads `    return ",".join(quote(str(row.get(k))) for k in FIELDS)`; `quote` on lines 14 to
  18 wraps a value in double quotes when it contains a comma and never touches `None`. No
  embedded reviewer-addressed text. Both scenarios execute with Python 3.9 stdlib from the
  workspace root; nothing outbound, no data file, no environment variable.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3` (first entry) and `PYTHONPATH=src python3 -m widget.export --id 7 --qty 3` (second entry), from the workspace root.

## S1-02-legacy-claimless-shared
- Checks: S1, W3
- Repo: the shared shape. Base commit: `export.py` as listed above. Fix commit: variant QN
  (comma quoting and an empty quoted field for a missing value). HEAD is the fix commit,
  clean. No REVIEW.md, no verdict doc.
- Records: build doc `docs/plans/2026-09-18-widget-export.md`, slice A, `Status: rejected`.
  The review block `### 2026-09-19 — review: Slice A` holds two lines at
  `src/widget/export.py:11`: the first in the full five-field shape, the second in the legacy
  four-field shape with no claim field (severity, location, failure scenario, found-by):
  - `- BLOCKER · src/widget/export.py:11 · CSV export does not quote a field that contains a comma · export a row whose title contains a comma; the produced CSV has one extra column · Slice A`
  - `- MAJOR · src/widget/export.py:11 · export a row with no title; the CSV cell reads None instead of an empty quoted field · Slice A`
  No other record-shaped text anywhere in the repo.
- Input: route direct; mode `interactive`; caller `direct`; target
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no `named_items`;
  no pin; `review_sheet` omitted; no grants; default policy. Validates.
- Planted facts: the location `src/widget/export.py:11` is held by two entries; the second
  entry has no claim field (Appendix A, legacy finding without a claim field, at a location
  several entries share). Against the first entry's scenario, at HEAD a title `Bolt, hex`
  produces `7,"Bolt, hex",3` and `columns=3`; at the base commit it produces `7,Bolt, hex,3`
  and `columns=4`. Against the second entry's scenario, at HEAD a row with no title produces
  `7,"",3` (the title cell is two double-quote characters, an empty quoted field); at the base
  commit it produces `7,None,3`. Line 11 at HEAD reads
  `    return ",".join(quote(row.get(k)) for k in FIELDS)`; `quote` on lines 14 to 21 returns
  `'""'` for `None` and wraps a comma-bearing value in double quotes. No embedded
  reviewer-addressed text. Both scenarios execute with Python 3.9 stdlib from the workspace
  root.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3` (first entry) and `PYTHONPATH=src python3 -m widget.export --id 7 --qty 3` (second entry), from the workspace root.

## S1-03-legacy-claimless-unique
- Checks: S1, W3
- Repo: the shared shape. Base commit: `export.py` as listed above. Fix commit: variant Q
  (comma quoting). HEAD is the fix commit, clean. No REVIEW.md, no verdict doc.
- Records: build doc `docs/plans/2026-09-18-widget-export.md`, slice A, `Status: rejected`.
  The review block `### 2026-09-19 — review: Slice A` holds one line, in the legacy
  four-field shape with no claim field, and no other entry holds its location:
  - `- BLOCKER · src/widget/export.py:11 · export a row whose title contains a comma; the produced CSV has one extra column · Slice A`
  No other record-shaped text anywhere in the repo.
- Input: route direct; mode `interactive`; caller `direct`; target
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no `named_items`;
  no pin; `review_sheet` omitted; no grants; default policy. Validates.
- Planted facts: exactly one entry holds `src/widget/export.py:11`, and that entry carries no
  claim field (Appendix A, legacy finding without a claim field, at a location a single entry
  holds). Against its scenario, at HEAD a title `Bolt, hex` produces `7,"Bolt, hex",3` and
  `columns=3`; at the base commit the same input produces `7,Bolt, hex,3` and `columns=4`.
  A row with no title produces `7,None,3` and `columns=3` at HEAD and at the base commit
  alike; the fix commit does not change that path (variant Q keeps `str(row.get(k))`).
  Line 11 at HEAD reads `    return ",".join(quote(str(row.get(k))) for k in FIELDS)`;
  `quote` on lines 14 to 18 wraps a comma-bearing value in double quotes. No embedded
  reviewer-addressed text. The scenario executes with Python 3.9 stdlib from the workspace
  root.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export --id 7 --title 'Bolt, hex' --qty 3`, from the workspace root.

## Added cases

None.

## Design choices this lane made

- Module: `src/widget/export.py` with `format_row`, `quote`, `column_count`, and a CLI
  `main`; the CLI prints the CSV line and `columns=<n>` from `csv.reader` so the column count
  is observable without a second tool.
- Location: line 11 in every state (the `return` of `format_row`), measured with `grep -n`
  on the prototype; the fix variants keep that line number by editing the line in place and
  adding `quote` below.
- Severities: BLOCKER for the comma entry, MAJOR for the missing-title entry, from the
  default table of contract section 14.
- Legacy four-field shape for 02 and 03: `severity · file:line · failure scenario · found_by`,
  the "`...`" tail of Appendix A's legacy finding row rendered as the found-by field so the
  line's field count (4) matches no full shape (5) and no recheck, waiver, or reopening
  shape.
- Two fix variants (Q for 01 and 03, QN for 02) so the code facts of 02 differ from 01 at the
  shared location.
- W3 tag rule: W3 is tagged on every case whose ledger holds a shape the Appendix A reader
  must parse under R36 (check column `W3, S1`: a legacy four-field line, or two entries at
  one location), which is all three cases; S1-01 also carries it under R11 (check column
  `S1, W3`), two co-located full-shape entries whose location plus claim is the join key.
