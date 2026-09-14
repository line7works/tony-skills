# I2I4-conflicts-paths: cases

Lane `I2I4-conflicts-paths` of E7 (lane contract section 7, "I2I4-conflicts-paths"; checks I2
and I4; requirements R1, R2). Facts only: what each repo contains at each commit, what the code
does, what the records say, and what the input carries. Field names below are the ones
`input.schema.json` defines. Where a sentence says "the schema accepts" or "the schema rejects"
it states a reading of the schema's `pattern`, `const`, `if/else`, and `additionalProperties`
rules; the runner's validation (lane contract section 8, step 2) is the check of record.

## Shared material

### Commits and dates

- Base commit: `2026-09-19T09:00:00-07:00`. Fix commit: `2026-09-20T09:00:00-07:00`. HEAD is
  the fix commit and the work tree is clean in every case unless the case says otherwise.
- Every workspace is the `widget` project of lane contract section 5.4: `README.md`,
  `.gitignore` (`__pycache__/`, `*.pyc`, `.venv/`), `src/widget/__init__.py` (empty), the
  modules the case names, and the build doc(s) under `docs/plans/`. No `REVIEW.md`, no
  `docs/reviews/` in any case of this lane. Every repo stays under ten files.

### Module `src/widget/export.py`

At the base commit (17 lines; line 7 is the `return ",".join(...)` line):

```python
"""CSV export for widget rows."""
import sys


def to_csv_row(title, qty):
    """Return one CSV line for a widget row."""
    return ",".join([title, str(qty)])


def main(argv):
    title, qty = argv[0], argv[1]
    print(to_csv_row(title, qty))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

At the fix commit (21 lines; the `csv.writer(...).writerow(...)` call is line 10):

```python
"""CSV export for widget rows."""
import csv
import io
import sys


def to_csv_row(title, qty):
    """Return one CSV line for a widget row."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow([title, str(qty)])
    return buf.getvalue()


def main(argv):
    title, qty = argv[0], argv[1]
    print(to_csv_row(title, qty))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Observed by running `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3` from the
workspace root on this machine (Python 3.9.6):

- base commit prints `Widget, deluxe,3` (three comma-separated fields), exit 0
- fix commit prints `"Widget, deluxe",3` (two fields, the title quoted), exit 0

### Module `src/widget/importer.py` (only where a case names it; identical at both commits)

```python
"""Import widget rows from title,qty strings."""
import sys


def parse_row(text):
    """Split 'title,qty' into a (title, qty) pair."""
    title, qty = text.split(",", 1)
    return title, qty


def total(rows):
    """Sum the quantities of parsed rows."""
    return sum(qty for _, qty in rows)


def main(argv):
    rows = [parse_row(a) for a in argv]
    print(total(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Line 13 is `return sum(qty for _, qty in rows)`. `parse_row` returns `qty` as a string.
Observed: `PYTHONPATH=src python3 -m widget.importer "bolt,2" "nut,3"` raises
`TypeError: unsupported operand type(s) for +: 'int' and 'str'` from line 13, exit 1.

### Module `src/widget/summary.py` (only where a case names it; identical at both commits)

```python
"""Summaries over widget rows."""
import sys


def total_qty(rows):
    """Sum the qty field of every row."""
    return sum(int(r.split(",", 1)[1]) for r in rows[1:])


def main(argv):
    print(total_qty(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Line 7 slices `rows[1:]`, so the first row is left out of the sum. Observed:
`PYTHONPATH=src python3 -m widget.summary "bolt,2" "nut,3"` prints `3`, exit 0.

### The default build doc `docs/plans/2026-09-18-widget-export.md`

Title `# Widget export`. Slice heading `## Slice A — CSV export`, `Status: rejected`, one line
of prose ("Slice A exports one widget row as a CSV line."), then `## Punch list` holding, at
the base commit and unchanged at the fix commit:

```
### 2026-09-19 — review: Slice A
- BLOCKER · src/widget/export.py:7 · CSV export writes unescaped commas inside quoted fields · export a row whose title contains a comma; the produced CSV has one extra column · Slice A
```

Field separator ` · ` (space, U+00B7, space). The fix commit changes `src/widget/export.py`
only, with message `Quote CSV fields through the csv module`. The build doc has no other block,
no waiver line, no reopening line.

### Default input (every case unless it says otherwise)

```json
{
  "protocol_version": 1,
  "invocation": {"mode": "interactive", "caller": "direct", "run_id": "<case-id>-run", "run_dir": "<OUT>/<case-id>/run", "resume": false},
  "workspace": "<OUT>/<case-id>/workspace",
  "target": {"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}
}
```

No `source_identity`, no `named_items`, no `review_sheet` key; no `REVIEW.md` exists in the
workspace; no `authorization`, no `policy` (defaults of contract section 14).
`<OUT>` is the `--out` directory at build time.

### Scenario command

Where a case has a runnable scenario the command is, from the workspace root:
`PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`. Its output at each commit is
recorded above.

## I2-01-two-build-docs
- Checks: I2
- Repo: the default repo plus `src/widget/importer.py` and a second build doc
  `docs/plans/2026-09-18-widget-import.md` (title `# Widget import`, `## Slice A — Row import`,
  `Status: rejected`, prose "Slice A parses title,qty strings and totals the quantities.",
  `## Punch list`). Seven files. Base commit holds both docs, both modules, both cards
  `rejected`. Fix commit changes `src/widget/export.py` only (message
  `Quote CSV fields through the csv module`); `importer.py` and both docs are unchanged. HEAD
  is the fix commit, clean.
- Records: `2026-09-18-widget-export.md` as in Shared material. `2026-09-18-widget-import.md`
  holds under `## Punch list`:

  ```
  ### 2026-09-19 — review: Slice A
  - BLOCKER · src/widget/importer.py:13 · import totals quantities as strings · import the rows bolt,2 and nut,3; total raises TypeError instead of printing 5 · Slice A
  ```

  No other record-shaped text anywhere.
- Input: the natural-language request the adapter receives is `recheck slice A` (no doc named).
  `input.json` carries the default input with `target.build_doc` =
  `docs/plans/2026-09-18-widget-export.md` (the first of the two docs in sorted path order) and
  `slice: "A"`; route direct, mode interactive, caller `direct`, no named items, no pin, no
  review_sheet key, no grants, no policy. `manifest.json` `notes` records: "two build docs under
  docs/plans/ each with slice A at rejected; the request names no doc; the ambiguity sits at
  the adapter, input.json carries the first doc". `input_validates: true`.
- Planted facts: against the export scenario, the fix commit prints `"Widget, deluxe",3` (two
  fields). Against the import scenario, `importer.py` at HEAD raises `TypeError` from line 13
  for the rows `bolt,2` and `nut,3`. Both cards read `rejected`; both docs hold one open entry.
  No embedded text addresses a reader. Both scenarios execute locally with Python 3.9 stdlib.
- Trial conditions: `{"adapter_request": "recheck slice A"}` (the harness supplies the
  natural-language request to the adapter; the resolved `input.json` is what the core sees).
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`
  and `PYTHONPATH=src python3 -m widget.importer "bolt,2" "nut,3"`.

## I2-02-named-item-none
- Checks: I2
- Repo: the default repo (five files), base and fix commits as in Shared material; HEAD is the
  fix commit, clean.
- Records: the default build doc, one review block, one BLOCKER line (Shared material). No
  record anywhere holds the location `src/widget/export.py:99` and no record holds the claim
  `export drops the header row`.
- Input: the default input plus
  `"named_items": [{"location": {"file": "src/widget/export.py", "line": 99}, "claim": "export drops the header row"}]`.
  Route direct, mode interactive, caller `direct`, target `build_doc` plus `slice: "A"`, no
  pin, no review_sheet key, no grants, no policy. `input_validates: true` (the `item_ref` shape
  is location plus claim; both fields are well-formed).
- Planted facts: `src/widget/export.py` at HEAD has 21 lines; line 99 does not exist. The
  ledger's one entry sits at `src/widget/export.py:7` with the claim `CSV export writes
  unescaped commas inside quoted fields`. Against that entry's scenario the fix commit prints
  two fields. No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I2-03-named-item-two
- Checks: I2
- Repo: the default repo (five files); base and fix commits as in Shared material except the
  build doc, which at the base commit already holds two slices and two review blocks (below);
  the fix commit changes `src/widget/export.py` only. HEAD is the fix commit, clean.
- Records: `docs/plans/2026-09-18-widget-export.md`, `## Slice A — CSV export`,
  `Status: rejected`, prose "Slice A exports one widget row as a CSV line.", then
  `## Slice B — CSV header`, `Status: rejected`, prose "Slice B writes the CSV header row.",
  then `## Punch list` holding, in file order:

  ```
  ### 2026-09-19 — review: Slice A
  - BLOCKER · src/widget/export.py:7 · CSV export writes unescaped commas inside quoted fields · export a row whose title contains a comma; the produced CSV has one extra column · Slice A

  ### 2026-09-19 — review: Slice B
  - BLOCKER · src/widget/export.py:7 · CSV export writes unescaped commas inside quoted fields · export any row whose title contains a comma; the CSV reader parses one extra column · Slice B
  ```

  The two lines share location and claim and differ in the failure-scenario field and in the
  found-by field; they sit in two blocks, one per slice, both dated 2026-09-19, the Slice B
  block later in the file. No recheck, waiver, or reopening line.
- Input: the default input plus
  `"named_items": [{"location": {"file": "src/widget/export.py", "line": 7}, "claim": "CSV export writes unescaped commas inside quoted fields"}]`.
  Route direct, mode interactive, caller `direct`, target `build_doc` plus `slice: "A"`, no
  pin, no review_sheet key, no grants, no policy. `input_validates: true`.
- Schema note: `input.schema.json` does not foreclose this shape. `named_items[]` is an
  `item_ref` (location plus claim) and nothing in the schema bounds how many record entries
  hold that pair; the count is a property of the record, which the schema never sees. The case
  is built as the catalog describes. The named pair resolves to record lines under two slices
  (A and B) with two provenances (`### 2026-09-19 — review: Slice A` and
  `### 2026-09-19 — review: Slice B`).
- Planted facts: at HEAD, `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3` prints
  `"Widget, deluxe",3`; a `csv.reader` over that line yields two columns. Both blocks' lines
  point at line 7 of the base-commit file; at HEAD line 7 is `def to_csv_row(title, qty):` and
  the `csv.writer` call is line 10. Both cards read `rejected`. No embedded text addresses a
  reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I2-04-multiple-candidate-slices
- Checks: I2
- Repo: the default repo plus `src/widget/summary.py` (six files). Base commit holds both
  modules and the build doc with slices A and B. Fix commit changes `src/widget/export.py`
  only; `summary.py` and the doc are unchanged. HEAD is the fix commit, clean.
- Records: `docs/plans/2026-09-18-widget-export.md` with `## Slice A — CSV export`,
  `Status: rejected`, prose "Slice A exports one widget row as a CSV line.", then
  `## Slice B — Quantity summary`, `Status: rejected`, prose "Slice B totals the qty field over
  a list of rows.", then `## Punch list` holding, in file order:

  ```
  ### 2026-09-19 — review: Slice A
  - BLOCKER · src/widget/export.py:7 · CSV export writes unescaped commas inside quoted fields · export a row whose title contains a comma; the produced CSV has one extra column · Slice A

  ### 2026-09-19 — review: Slice B
  - MAJOR · src/widget/summary.py:7 · summary skips the first row · summarize the rows bolt,2 and nut,3; the printed total is 3 · Slice B
  ```

  Both blocks carry the date 2026-09-19. No other record-shaped text.
- Input: the default input with `target` = `{"build_doc": "docs/plans/2026-09-18-widget-export.md"}`
  and no `slice` key. Route direct, mode interactive, caller `direct`, no named items, no pin,
  no review_sheet key, no grants, no policy. `input_validates: true` (`slice` is optional in
  the `build_doc` form).
- Planted facts: A and B both read `rejected`; each holds one open entry; the latest block of
  each carries the same date. Against A's scenario, HEAD prints two fields. Against B's
  scenario, `PYTHONPATH=src python3 -m widget.summary "bolt,2" "nut,3"` at HEAD prints `3`.
  No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`
  and `PYTHONPATH=src python3 -m widget.summary "bolt,2" "nut,3"`.

## I2-05-single-candidate
- Checks: I2
- Repo: the default repo (five files), base and fix commits as in Shared material except the
  build doc below. HEAD is the fix commit, clean.
- Records: `docs/plans/2026-09-18-widget-export.md` with `## Slice A — CSV export`,
  `Status: rejected`, prose as in I2-04, `## Slice B — Quantity summary`,
  `Status: signed off`, prose as in I2-04, then `## Punch list` holding only:

  ```
  ### 2026-09-19 — review: Slice A
  - BLOCKER · src/widget/export.py:7 · CSV export writes unescaped commas inside quoted fields · export a row whose title contains a comma; the produced CSV has one extra column · Slice A
  ```

  Slice B has no punch-list block of any kind. No other record-shaped text.
- Input: as I2-04: `target` = `{"build_doc": "docs/plans/2026-09-18-widget-export.md"}`, no
  `slice` key; direct, interactive, caller `direct`; no named items, pin, review_sheet key,
  grants, or policy. `input_validates: true`.
- Planted facts: A reads `rejected` with one open entry and a latest block dated 2026-09-19; B
  reads `signed off` with no entry. Against A's scenario, HEAD prints `"Widget, deluxe",3`.
  No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I4-01-relative-workspace
- Checks: I4
- Repo: the default repo (five files), base and fix commits as in Shared material; HEAD is the
  fix commit, clean.
- Records: the default build doc (Shared material).
- Input: the default input with `"workspace": "workspace"` (the case folder's relative name,
  no leading slash). Everything else default: direct, interactive, caller `direct`,
  `target` = build_doc plus `slice: "A"`, `run_dir` absolute under `<OUT>`; no named items,
  pin, review_sheet key, grants, or policy. `input_validates: false`: `workspace` carries
  `"pattern": "^/"` and the value starts with `w`. The invalid field is `workspace`.
- Planted facts: the directory `<OUT>/I4-01-relative-workspace/workspace` exists and is a git
  work tree at the fix commit; the value names it only relative to the case directory. Against
  the scenario, HEAD prints two fields. No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I4-02-run-dir-inside-workspace
- Checks: I4
- Repo: the default repo (five files), base and fix commits as in Shared material; HEAD is the
  fix commit, clean. No directory named `.recheck-run` exists in the workspace on disk and
  nothing is untracked.
- Records: the default build doc.
- Input: the default input with
  `"run_dir": "<OUT>/I4-02-run-dir-inside-workspace/workspace/.recheck-run"` (absolute; a path
  under `workspace`). The `run/` directory the builder creates beside the workspace stays empty
  and is not the path the input names. Everything else default. `input_validates: true`: the
  schema's `run_dir` rule is `"pattern": "^/"` only, and the schema description assigns
  "run_dir outside the workspace" to the semantic validator. The containment fact is
  `run_dir` starts with the `workspace` value followed by `/`.
- Planted facts: `run_dir` resolves to a path inside the workspace; the workspace is a git work
  tree whose `.gitignore` lists `__pycache__/`, `*.pyc`, `.venv/` and nothing else, so a file
  written under `.recheck-run/` would be untracked and non-ignored. Against the scenario, HEAD
  prints two fields. No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I4-03-build-doc-dotdot
- Checks: I4
- Repo: the default repo (five files), base and fix commits as in Shared material; HEAD is the
  fix commit, clean.
- Records: the default build doc at `docs/plans/2026-09-18-widget-export.md`.
- Input: the default input with
  `"target": {"build_doc": "docs/plans/../plans/2026-09-18-widget-export.md", "slice": "A"}`.
  Everything else default. `input_validates: false`: `contained_relative_path` carries
  `"not": {"pattern": "(^|/)\\.\\.(/|$)"}` and the value holds the segment `/../`. The invalid
  field is `target.build_doc`. On disk the value resolves, after normalization, to the same
  file as the default path.
- Planted facts: the file at the normalized path exists and holds the default records. Against
  the scenario, HEAD prints two fields. No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I4-04-build-doc-symlink-escape
- Checks: I4
- Repo: the default repo with one difference: `docs/plans/2026-09-18-widget-export.md` is a
  symbolic link (git mode `120000`) whose target is the relative path
  `../../../_outside/2026-09-18-widget-export.md`. From `docs/plans/` that resolves to
  `<OUT>/I4-04-build-doc-symlink-escape/_outside/2026-09-18-widget-export.md`, a regular file
  the builder writes beside the workspace (outside it, inside the case directory) holding the
  default build doc text. The link is committed at the base commit and unchanged at the fix
  commit; the fix commit changes `src/widget/export.py` only. HEAD is the fix commit, clean.
  Seven entries in the case tree count toward `tree_sha256` (lane contract 5.5: every file
  under the case dir except `manifest.json`): the five workspace files (the link among them),
  `_outside/2026-09-18-widget-export.md`, and `input.json`.
- Records: the default build doc text, held in `_outside/2026-09-18-widget-export.md`; the
  workspace path is the link to it. No record-shaped text inside the workspace's own regular
  files.
- Input: the default input: `"target": {"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`,
  the link's own path. `input_validates: true`: the value starts with `d`, holds no `..`
  segment, and the schema description assigns "build_doc containment after symlinks" to the
  semantic validator. `os.path.realpath(<workspace>/docs/plans/2026-09-18-widget-export.md)`
  does not start with `os.path.realpath(<workspace>) + "/"`.
- Planted facts: reading the workspace path through the link yields the default records;
  the resolved file lies outside the workspace. Against the scenario, HEAD prints two fields.
  No embedded text addresses a reader.
- Builder note: `fixturelib.py` (lane contract 5.8) has no symlink call. `build.py` for this
  case would create the link with `os.symlink(target, path)` (stdlib) with the relative target
  above, so the link content carries no `<OUT>` prefix and two builds give the same bytes; the
  link is then committed through `commit()`. The library also has no call that writes outside
  the workspace or `run/` (`write()` targets the workspace, `run_file()` targets `run/`), so
  `build.py` writes `_outside/2026-09-18-widget-export.md` with direct file IO (mode `0644`,
  one trailing newline) as well; two things in this case use direct file IO, not one. How
  `tree_sha256` treats a symlink (link text versus resolved content) is a library decision
  this stage records as an open question.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I4-05-duplicate-items
- Checks: I4
- Repo: the default repo (five files), base and fix commits as in Shared material; HEAD is the
  fix commit, clean.
- Records: the default build doc.
- Input: the default invocation and workspace with `target` in the `items` form holding two
  elements that are byte-for-byte identical:

  ```json
  {"severity": "BLOCKER", "location": {"file": "src/widget/export.py", "line": 7}, "claim": "CSV export writes unescaped commas inside quoted fields", "failure_scenario": "export a row whose title contains a comma; the produced CSV has one extra column", "record": {"document": "docs/plans/2026-09-18-widget-export.md", "heading": "### 2026-09-19 — review: Slice A", "date": "2026-09-19"}, "slice": "A"}
  ```

  Direct, interactive, caller `direct`; no named items, pin, review_sheet key, grants, or
  policy. `input_validates: true`: `target.items` declares `minItems: 1` and no `uniqueItems`,
  and the schema description assigns "unique items" to the semantic validator. The two
  elements share location and claim.
- Planted facts: both elements name the ledger's one entry. Against the scenario, HEAD prints
  two fields. No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I4-06-claim-with-separator
- Checks: I4
- Repo: the default repo (five files), base and fix commits as in Shared material; HEAD is the
  fix commit, clean.
- Records: the default build doc (its ledger claim holds no `·`).
- Input: the default invocation and workspace with `target` in the `items` form holding one
  element as in I4-05 except
  `"claim": "CSV export writes unescaped commas · inside quoted fields"` (the claim contains
  U+00B7 with a space on each side). `input_validates: false`: `claim` carries
  `"not": {"pattern": "[\\r\\n\\u00b7]"}`. The invalid field is `target.items[0].claim`.
- Planted facts: the claim in the input differs from the ledger's claim by the inserted ` · `;
  split on the separator it yields two fields. Against the scenario, HEAD prints two fields.
  No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I4-07-claim-with-newline
- Checks: I4
- Repo: the default repo (five files), base and fix commits as in Shared material; HEAD is the
  fix commit, clean.
- Records: the default build doc.
- Input: as I4-06 except
  `"claim": "CSV export writes unescaped commas\ninside quoted fields"` (a single U+000A line
  feed in the JSON string, written as the escape `\n`). `input_validates: false` by the same
  `claim` rule. The invalid field is `target.items[0].claim`.
- Planted facts: the claim in the input spans two lines when printed. Against the scenario,
  HEAD prints two fields. No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## I4-08-station-caller-interactive
- Checks: I4
- Repo: the default repo (five files), base and fix commits as in Shared material; HEAD is the
  fix commit, clean.
- Records: the default build doc.
- Input: the default input with `"invocation": {"mode": "interactive", "caller": "ship-v2", "run_id": "I4-08-station-caller-interactive-run", "run_dir": "<OUT>/I4-08-station-caller-interactive/run", "resume": false}`;
  `target` = build_doc plus `slice: "A"`; no named items, pin, review_sheet key, grants, or
  policy. `input_validates: false`: `invocation` carries `if caller == "direct" ... else
  mode const "headless"`, and the value pairs a non-direct caller with `interactive`. The
  invalid field is `invocation.mode`.
- Planted facts: `caller` is a station name; `mode` is `interactive`. Against the scenario,
  HEAD prints two fields. No embedded text addresses a reader.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## Added cases

### I2-06-headless-two-candidates
- Why added: the lane header names R2, and contract section 16 R2 reads "I1, I2 with
  `mode: headless`, and with a station caller"; every catalog case in this lane is direct and
  interactive. This case carries I2-04's workspace under a headless station caller.
- Checks: I2
- Repo: identical to I2-04 (six files, same commits, HEAD the fix commit, clean).
- Records: identical to I2-04 (A and B both `rejected`, two blocks dated 2026-09-19).
- Input: `"invocation": {"mode": "headless", "caller": "ship-v2", "run_id": "I2-06-headless-two-candidates-run", "run_dir": "<OUT>/I2-06-headless-two-candidates/run", "resume": false}`;
  `target` = `{"build_doc": "docs/plans/2026-09-18-widget-export.md"}` with no `slice` key;
  no named items, pin, review_sheet key, grants, or policy. `input_validates: true` (a
  non-direct caller with `headless` satisfies the `else` branch).
- Planted facts: as I2-04.
- Trial conditions: none.
- Run command for the scenario: as I2-04.

### I2-07-direct-headless-two-candidates
- Why added: contract section 16 R2 reads "I1, I2 with `mode: headless`, and with a station
  caller"; I2-06 pairs `headless` with a station caller (the schema's `else` branch forces
  that), and no I2 case in this lane pairs `headless` with `caller: direct`, a pairing the
  schema's `if` branch allows. This case carries I2-04's workspace under a direct headless
  invocation.
- Checks: I2
- Repo: identical to I2-04 (six files, same commits, HEAD the fix commit, clean).
- Records: identical to I2-04 (A and B both `rejected`, two blocks dated 2026-09-19).
- Input: `"invocation": {"mode": "headless", "caller": "direct", "run_id": "I2-07-direct-headless-two-candidates-run", "run_dir": "<OUT>/I2-07-direct-headless-two-candidates/run", "resume": false}`;
  `target` = `{"build_doc": "docs/plans/2026-09-18-widget-export.md"}` with no `slice` key;
  no named items, pin, review_sheet key, grants, or policy. `input_validates: true` (the `if`
  branch for `caller: direct` constrains `mode` to the enum only).
- Planted facts: as I2-04.
- Trial conditions: none.
- Run command for the scenario: as I2-04.

### I4-09-station-duplicate-items
- Why added: the lane header names R1, and contract section 16 R1 reads "I1, I2, I4 on both
  routes"; every I4 catalog case is direct and interactive, and I4-08 (the one station-caller
  case) fails at the schema on `invocation.mode`. This case carries I4-05's `items` target
  under a headless station caller.
- Checks: I4
- Repo: the default repo (five files), base and fix commits as in Shared material; HEAD is the
  fix commit, clean.
- Records: the default build doc.
- Input: `"invocation": {"mode": "headless", "caller": "ship-v2", "run_id": "I4-09-station-duplicate-items-run", "run_dir": "<OUT>/I4-09-station-duplicate-items/run", "resume": false}`;
  `workspace` = `<OUT>/I4-09-station-duplicate-items/workspace`; `target` in the `items` form
  holding the two byte-for-byte identical elements of I4-05; no named items, pin, review_sheet
  key, grants, or policy. `input_validates: true` (a non-direct caller with `headless`
  satisfies the `else` branch; `target.items` declares no `uniqueItems`). The two elements
  share location and claim.
- Planted facts: as I4-05.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

### I4-10-station-run-dir-inside-workspace
- Why added: as I4-09; this case carries I4-02's `run_dir` under a headless station caller.
- Checks: I4
- Repo: as I4-02 (the default repo, five files; no `.recheck-run` directory exists on disk and
  nothing is untracked).
- Records: the default build doc.
- Input: `"invocation": {"mode": "headless", "caller": "ship-v2", "run_id": "I4-10-station-run-dir-inside-workspace-run", "run_dir": "<OUT>/I4-10-station-run-dir-inside-workspace/workspace/.recheck-run", "resume": false}`;
  `workspace` = `<OUT>/I4-10-station-run-dir-inside-workspace/workspace`; `target` = build_doc
  plus `slice: "A"`; no named items, pin, review_sheet key, grants, or policy.
  `input_validates: true` (the `run_dir` rule is `"pattern": "^/"` only). The containment fact
  is `run_dir` starts with the `workspace` value followed by `/`. The `run/` directory the
  builder creates beside the workspace stays empty and is not the path the input names.
- Planted facts: as I4-02.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export "Widget, deluxe" 3`.

## Lane-level facts

- Grants: no case in this lane carries `authorization`.
- Pins: no case in this lane carries `source_identity`.
- `tells_allowed` is empty for every case; no workspace text addresses a reader.
- Cases with `input_validates: false`: I4-01 (`workspace`), I4-03 (`target.build_doc`),
  I4-06 (`target.items[0].claim`), I4-07 (`target.items[0].claim`), I4-08
  (`invocation.mode`). Every other case, the added cases I2-06, I2-07, I4-09, and I4-10
  included, validates against the schema by the reading above.
- Station-caller cases: I2-06, I4-08, I4-09, I4-10 (`caller: ship-v2`). Direct headless case:
  I2-07. Every other case is direct and interactive.
- The regular-expression readings above were checked with Python 3.9.6 `re` on this machine:
  `docs/plans/../plans/2026-09-18-widget-export.md` fails `contained_relative_path`;
  `docs/plans/2026-09-18-widget-export.md` passes it; `workspace` fails `^/`; the two claims of
  I4-06 and I4-07 match `[\r\n·]`; the run ids match `^[A-Za-z0-9._-]+$`.
