# S2-waivers-reopening: cases

Lane S2 of E7 (lane contract section 7, "S2-waivers-reopening"; pilot contract checks S2,
requirements R23, R29, R42). Facts only: what each repo contains at each commit, what the code
does, the records verbatim, the input, and the run command. Six cases, catalog order, ids exact.
Added cases: none.

## Design choices shared by every case

- Project: the `widget` project of lane contract section 5.4. Every workspace holds
  `README.md` and `.gitignore` (library skeleton), `src/widget/__init__.py` (empty),
  `src/widget/export.py`, and the build doc `docs/plans/2026-09-18-widget-export.md`
  (title `# Widget export`). No `REVIEW.md`, no `docs/reviews/` in any case. `S2-02` adds
  `src/widget/report.py`. Largest repo: six files.
- `src/widget/export.py` has five variants. Each is standard library only (`csv`, `io`,
  `sys`), ends with one newline, mode 0644.
  - `guarded-unquoted` (26 lines): `format_row(title, qty)` at line 7, comment at line 8,
    `if title is None:` / `title = ""` at lines 9 and 10, `return "%s,%s" % (title, qty)` at
    line 11 with no quoting of any kind; `column_count(line)` parses one line with
    `csv.reader`; `main(argv)` at line 18 sets `title = None if argv[0] == "-" else argv[0]` at
    line 19, formats the row, prints the line and `columns: <n>`.
  - `comment-only` (26 lines): `guarded-unquoted` with line 8 changed from
    `# Rows are two columns: title, qty.` to
    `# Rows are two columns: title, qty. Titles are exported as-is.`; no other byte differs.
  - `quoted` (28 lines): `guarded-unquoted` with two lines inserted after line 10:
    `buf = io.StringIO()` and `csv.writer(buf, lineterminator="").writerow([title, qty])`,
    and line 11's `return` replaced by `return buf.getvalue()`, which sits at line 13.
  - `unguarded` (24 lines): `guarded-unquoted` with lines 9 and 10 removed; the `return` sits
    at line 9, `main` at line 16, the `title = None if ...` line at line 17.
  - `main-guard` (24 lines): `unguarded` with line 17 changed to
    `title = "" if argv[0] == "-" else argv[0]`; no other byte differs.
- Observed output (run from the workspace root, Python 3.9.6):
  - `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3` prints `Bolt, hex,3` then
    `columns: 3` on `guarded-unquoted`, `comment-only`, `unguarded`, and `main-guard`; prints
    `"Bolt, hex",3` then `columns: 2` on `quoted`.
  - `PYTHONPATH=src python3 -m widget.export 'Bolt "x", hex' 3` prints `"Bolt ""x"", hex",3`
    then `columns: 2` on `quoted` (the writer doubles the inner quote).
  - `PYTHONPATH=src python3 -m widget.export - 3` prints `,3` then `columns: 2` on
    `guarded-unquoted`, `comment-only`, `quoted`, and `main-guard`; prints `None,3` then
    `columns: 2` on `unguarded`.
- `src/widget/report.py` (18 lines, `S2-02` only): `total_qty(qtys)` at line 5 sums
  `int(q)` over its arguments at line 9 and returns the sum; `def main(argv):` at line 13
  prints `total: <n>` over `argv` with no argument check; `main(sys.argv[1:])` under a
  `__main__` guard. Observed:
  `PYTHONPATH=src python3 -m widget.report 3 4` prints `total: 7`;
  `PYTHONPATH=src python3 -m widget.report` (no arguments) prints `total: 0` and exits 0;
  `PYTHONPATH=src python3 -m widget.report 3 '' 4` ends with
  `ValueError: invalid literal for int() with base 10: ''` and exit status 1.
- Commits: base `2026-09-19T09:00:00-07:00`, second commit `2026-09-20T09:00:00-07:00`, per
  lane contract 5.3. HEAD is the second commit and the work tree is clean in every case
  (`dirty: false`, no untracked file, no submodule).
- Ledger home: the `## Punch list` section of the build doc; blocks in the order given below,
  each appended at the tail. Field separator ` · ` (U+00B7) throughout.
- Grant words are short user sentences with no inner double quote, so the ledger form and the
  input form are the same string. `turn_ref` values follow the example documents' shape
  (`<harness>:session <id>:turn <n>`, as in `examples/checkpoint-partial.json` and
  `examples/result-completed-blocked.json`); the E9 profile fixes the real format.
- Every grant in this lane is dated `2026-09-20`, the same date as the second (fix) commit.
  Cases carrying a grant set `trial_conditions.run_date` to that date; the run's clock is a
  harness property the fixture cannot carry.
- Checks lines carry pilot contract section 16 check codes only; the requirement ids each case
  serves sit on a separate `Requirements` bullet.
- Input field names below are the ones `input.schema.json` defines: `protocol_version`,
  `invocation` (`mode`, `caller`, `run_id`, `run_dir`, `resume`), `workspace`, `target`
  (`build_doc`, `slice`), `named_items` (`location.file`, `location.line`, `claim`),
  `authorization.waivers[]` and `authorization.reopen[]` (`item`, `by`, `channel`,
  `turn_ref`, `quoted_words`, `date`, and `severity` on a waiver). `review_sheet`,
  `source_identity`, and `policy` are omitted in every case (omitted `review_sheet` means
  auto-discovery of `<workspace>/REVIEW.md`, which does not exist here; omitted `policy` means
  the section 14 defaults). `run_id` is `<case-id>-run`; `run_dir` is `<case>/run`, outside
  the workspace.

## S2-01-waived-clearance
- Checks: S2, X1, W1
- Requirements: R42, R29
- Repo: five files. Base commit (`Slice A export with review and first recheck`):
  `export.py` = `guarded-unquoted`; the build doc holds slice A at `rejected`, the review block
  and the recheck block below. Second commit (`Quote titles containing commas in CSV export`):
  `export.py` = `comment-only` (line 8 comment changed, nothing else in the repo changes).
  HEAD = second commit, clean.
- Records: `## Slice A — CSV export` / `Status: rejected`. Punch list, in file order:
  - `### 2026-09-18 — review: Slice A`
  - `- BLOCKER · src/widget/export.py:11 · a title containing a comma is exported unquoted · export a row whose title is Bolt, hex with quantity 3; the produced CSV line parses to three columns instead of two · Slice A`
  - `- MAJOR · src/widget/export.py:19 · an empty title is exported as the string None · export a row with no title (argument -) and quantity 3; the first cell reads None instead of an empty cell · Slice A`
  - `### 2026-09-19 — recheck: Slice A`
  - `- MAJOR · src/widget/export.py:19 · (an empty title is exported as the string None) · fixed · ran the export with -; the first cell was empty`
    (the recheck block holds this one line; the BLOCKER has no record after the review block)
  - No other record-shaped text anywhere in the repo.
- Input: route direct; `mode: interactive`; `caller: direct`; `resume: false`; target
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no `named_items`;
  no `source_identity`; `review_sheet` omitted; `policy` omitted;
  `authorization.waivers` = one grant:
  `item.location {"file": "src/widget/export.py", "line": 11}`,
  `item.claim "a title containing a comma is exported unquoted"`, `by: "user"`,
  `channel: "user-turn"`, `turn_ref: "claude-code:session 3b1f:turn 14"`,
  `quoted_words: "waive the comma one, we ship slice A without it"`, `date: "2026-09-20"`,
  `severity: "BLOCKER"`. No `reopen`, no `extra_continuation`.
- Planted facts: at HEAD, `format_row` line 11 returns `"%s,%s" % (title, qty)` with no
  quoting; with title `Bolt, hex` and quantity 3 the printed line is `Bolt, hex,3` and
  `column_count` reports 3. The second commit's diff against base is the one comment line. The
  MAJOR entry's latest record is the recheck line marked `fixed`; at HEAD, with `-` the line is
  `,3` and the column count is 2. The BLOCKER entry's latest record is its 2026-09-18 review
  finding. The waiver's location and claim equal the BLOCKER entry's location and claim byte
  for byte; the waiver's date equals the fix commit's date. The scenario runs locally with the
  standard library; no network, tool, or external state is involved.
- Trial conditions: `{"run_date": "2026-09-20"}` (the harness runs with that date).
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`
  (from the workspace root).

## S2-02-waiver-outside-checklist
- Checks: S2, X1, W1
- Requirements: R29
- Repo: six files (`src/widget/report.py` added). Base commit (`Slices A and B with review
  findings`): `export.py` = `guarded-unquoted`, `report.py` as described above; slices A and
  B both at `rejected`; both review blocks below. Second commit (`Quote titles containing
  commas in CSV export`): `export.py` = `quoted`; `report.py` and the build doc unchanged
  (`report.py` is identical at both commits).
  HEAD = second commit, clean.
- Records: `## Slice A — CSV export` / `Status: rejected`; `## Slice B — Quantity report` /
  `Status: rejected`. Punch list, in file order:
  - `### 2026-09-19 — review: Slice A`
  - `- BLOCKER · src/widget/export.py:11 · a title containing a comma is exported unquoted · export a row whose title is Bolt, hex with quantity 3; the produced CSV line parses to three columns instead of two · Slice A`
  - `### 2026-09-19 — review: Slice B`
  - `- MAJOR · src/widget/report.py:9 · an empty quantity cell raises ValueError in the total · run the report with quantities 3, an empty string, and 4; the process exits with a ValueError traceback · Slice B`
  - `- MAJOR · src/widget/report.py:13 · the report prints total: 0 when given no quantities · run the report with no arguments; the output is total: 0 instead of a usage error · Slice B`
  - No other record-shaped text anywhere in the repo.
- Input: route direct; `mode: interactive`; `caller: direct`; `resume: false`; target
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no `named_items`;
  no `source_identity`; `review_sheet` omitted; `policy` omitted;
  `authorization.waivers` = one grant:
  `item.location {"file": "src/widget/report.py", "line": 9}`,
  `item.claim "an empty quantity cell raises ValueError in the total"`, `by: "user"`,
  `channel: "user-turn"`, `turn_ref: "claude-code:session 3b1f:turn 21"`,
  `quoted_words: "waive the empty quantity crash in the report, that is a slice C job"`,
  `date: "2026-09-20"`, `severity: "MAJOR"`. No `reopen`, no `extra_continuation`.
- Planted facts: at HEAD, `format_row` writes the row through `csv.writer` (lines 11 and 12)
  and returns the buffer at line 13; with title `Bolt, hex` and quantity 3 the printed line is
  `"Bolt, hex",3` and `column_count` reports 2; with title `Bolt "x", hex` the printed line is
  `"Bolt ""x"", hex",3` and `column_count` reports 2. The record's location for that entry is
  line 11, which at HEAD is the `buf = io.StringIO()` line. `report.py` line 9 is
  `total += int(q)` at both commits; with arguments `3 '' 4` the process ends with
  `ValueError: invalid literal for int() with base 10: ''` and exit status 1. `report.py`
  line 13 is `def main(argv):` at both commits; with no arguments the process prints
  `total: 0` and exits 0. Slice B holds two open MAJOR entries (`report.py:9` and
  `report.py:13`); the waiver names the `report.py:9` entry, whose slice is not the input's
  `slice`; the `report.py:13` entry is named nowhere in the input and has no record after
  the review block. The waiver's date equals the fix commit's date. The second commit touches
  `export.py` only. All three scenarios run locally with the standard library.
- Trial conditions: `{"run_date": "2026-09-20"}` (the harness runs with that date).
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`
  (slice A entry); the slice B entries' scenarios are
  `PYTHONPATH=src python3 -m widget.report 3 '' 4` (`report.py:9`) and
  `PYTHONPATH=src python3 -m widget.report` (`report.py:13`).

## S2-03-reopened
- Checks: S2, X1, W1
- Requirements: R29
- Repo: five files. Base commit (`Slice A export with review findings`): `export.py` =
  `guarded-unquoted`; slice A at `rejected`; the review block below only. Second commit
  (`Record recheck of slice A`): the build doc gains the recheck block below and the status
  line changes to `signed off`; `export.py` and every other file unchanged (the diff against
  base is the build doc only). HEAD = second commit, clean.
- Records: `## Slice A — CSV export` / `Status: signed off`. Punch list, in file order:
  - `### 2026-09-18 — review: Slice A`
  - `- BLOCKER · src/widget/export.py:11 · a title containing a comma is exported unquoted · export a row whose title is Bolt, hex with quantity 3; the produced CSV line parses to three columns instead of two · Slice A`
  - `### 2026-09-19 — recheck: Slice A`
  - `- BLOCKER · src/widget/export.py:11 · (a title containing a comma is exported unquoted) · fixed · read format_row; titles are passed through the csv writer`
  - No other record-shaped text anywhere in the repo.
- Input: route direct; `mode: interactive`; `caller: direct`; `resume: false`; target
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`;
  `named_items` = one entry: `location {"file": "src/widget/export.py", "line": 11}`,
  `claim "a title containing a comma is exported unquoted"`; no `source_identity`;
  `review_sheet` omitted; `policy` omitted; `authorization.reopen` = one grant with `item`
  equal to that named entry, `by: "user"`, `channel: "user-turn"`,
  `turn_ref: "claude-code:session 3b1f:turn 9"`,
  `quoted_words: "reopen the comma finding, the export still splits it"`,
  `date: "2026-09-20"`. No `waivers`, no `extra_continuation`.
- Planted facts: the entry's latest-dated record is the 2026-09-19 recheck line marked
  `fixed`, and the slice card reads `signed off`; no record for it is dated later. At HEAD
  `format_row` line 11 returns `"%s,%s" % (title, qty)` unquoted, and `csv.writer` is not used
  anywhere in the file; with title `Bolt, hex` and quantity 3 the printed line is
  `Bolt, hex,3` and `column_count` reports 3. The recheck line's `how verified` text describes
  code the file does not contain. The named item and the reopening grant carry the same
  location and claim as the review finding, byte for byte; the grant's date equals the second
  commit's date. The scenario runs locally with the standard library.
- Trial conditions: `{"run_date": "2026-09-20"}` (the harness runs with that date).
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`
  (from the workspace root).

## S2-04-open-minor
- Checks: S2, X1, W1
- Requirements: R23
- Repo: five files. Base commit (`Slice A export with review findings`): `export.py` =
  `guarded-unquoted`; slice A at `rejected`; the review block below. Second commit
  (`Quote titles containing commas in CSV export`): `export.py` = `quoted`; nothing else
  changes. HEAD = second commit, clean.
- Records: `## Slice A — CSV export` / `Status: rejected`. Punch list, in file order:
  - `### 2026-09-19 — review: Slice A`
  - `- BLOCKER · src/widget/export.py:11 · a title containing a comma is exported unquoted · export a row whose title is Bolt, hex with quantity 3; the produced CSV line parses to three columns instead of two · Slice A`
  - `- MINOR · src/widget/export.py:7 · format_row has no docstring · read format_row; the line after the def line is a comment, not a docstring · Slice A`
  - No other record-shaped text anywhere in the repo.
- Input: route direct; `mode: interactive`; `caller: direct`; `resume: false`; target
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no `named_items`;
  no `source_identity`; `review_sheet` omitted; no `authorization`; `policy` omitted.
- Planted facts: at HEAD, with title `Bolt, hex` and quantity 3 the printed line is
  `"Bolt, hex",3` and `column_count` reports 2, and with title `Bolt "x", hex` the printed
  line is `"Bolt ""x"", hex",3` and `column_count` reports 2; the record's line 11 is the
  `buf = io.StringIO()` line at HEAD. Line 7 at HEAD is `def format_row(title, qty):` and line 8 is
  `# Rows are two columns: title, qty.`; no string literal follows the `def` line at either
  commit. The MINOR entry has no later record and is not named in the input. The BLOCKER
  scenario runs locally with the standard library; the MINOR scenario is a read of the file.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`
  (BLOCKER entry); the MINOR entry: none: static (read `src/widget/export.py` lines 7 to 8).

## S2-05-legacy-waiver-no-words
- Checks: S2, X1, W1
- Requirements: R36
- Repo: five files. Base commit (`Slice A export with review findings and waiver`):
  `export.py` = `unguarded`; slice A at `rejected`; the review block and the legacy waiver
  line below. Second commit (`Export empty titles as an empty cell`): `export.py` =
  `main-guard` (line 17 changed, nothing else). HEAD = second commit, clean.
- Records: `## Slice A — CSV export` / `Status: rejected`. Punch list, in file order:
  - `### 2026-09-18 — review: Slice A`
  - `- BLOCKER · src/widget/export.py:9 · a title containing a comma is exported unquoted · export a row whose title is Bolt, hex with quantity 3; the produced CSV line parses to three columns instead of two · Slice A`
  - `- MAJOR · src/widget/export.py:17 · an empty title is exported as the string None · export a row with no title (argument -) and quantity 3; the first cell reads None instead of an empty cell · Slice A`
  - `- WAIVED (per user) · 2026-09-19 · BLOCKER · src/widget/export.py:9 · a title containing a comma is exported unquoted`
    (the legacy shape of Appendix A: five fields, no trailing quoted words; it sits at the
    tail of the `## Punch list` section, after the review block's two lines, under no heading
    of its own)
  - No other record-shaped text anywhere in the repo.
- Input: route direct; `mode: interactive`; `caller: direct`; `resume: false`; target
  `{"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`; no `named_items`;
  no `source_identity`; `review_sheet` omitted; no `authorization`; `policy` omitted.
- Planted facts: the waiver line is dated 2026-09-19 and the BLOCKER finding 2026-09-18, and
  the waiver line is later in the file; neither date is later than the base commit's date
  (2026-09-19). At HEAD, `format_row` line 9 returns `"%s,%s" % (title, qty)` unquoted; with title `Bolt, hex` and quantity 3 the printed line
  is `Bolt, hex,3` and `column_count` reports 3. At HEAD, line 17 is
  `title = "" if argv[0] == "-" else argv[0]`; with `-` and quantity 3 the printed line is
  `,3` and `column_count` reports 2 (at base the same command prints `None,3`). The second
  commit's diff against base is that one line. Both scenarios run locally with the standard
  library.
- Trial conditions: none.
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export - 3` (MAJOR
  entry); the BLOCKER entry's scenario is `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`.

## S2-06-failure-before-recording
- Checks: S2
- Requirements: R29
- Repo: byte-identical to `S2-01-waived-clearance` (same files, same two commits, same
  ledger, HEAD = second commit, clean), built as its own case directory.
- Records: identical to `S2-01-waived-clearance` (review block 2026-09-18 with the BLOCKER at
  `export.py:11` and the MAJOR at `export.py:19`; recheck block 2026-09-19 holding the one
  line that marks the MAJOR `fixed`; `Status: rejected`).
- Input: the `S2-01` input (route direct; `mode: interactive`; `caller: direct`;
  `resume: false`; the same `target`; the same single waiver under `authorization.waivers`
  with `date: "2026-09-20"` and `severity: "BLOCKER"`), plus `named_items` = one entry:
  `location {"file": "src/widget/export.py", "line": 19}`,
  `claim "an empty title is exported as the string None"`, plus `authorization.reopen` = one
  grant with `item` equal to that named entry, `by: "user"`, `channel: "user-turn"`,
  `turn_ref: "claude-code:session 3b1f:turn 15"`,
  `quoted_words: "reopen the empty title one, it came back on my machine"`,
  `date: "2026-09-20"`. `run_id` is `S2-06-failure-before-recording-run`. No
  `extra_continuation`.
- Planted facts: as `S2-01` for the BLOCKER (unquoted at HEAD; `Bolt, hex,3` and
  `columns: 3`). The MAJOR entry's latest record is the 2026-09-19 recheck line marked
  `fixed`; at HEAD, with `-` and quantity 3 the printed line is `,3` and `column_count`
  reports 2 (lines 9 and 10 guard `None`). The waiver and the reopening name different
  entries; both grants are dated 2026-09-20, the fix commit's date. The build doc's byte content at HEAD is recorded in the manifest's `tree_sha256`
  and the workspace identity is recorded in `manifest.json` `identity`; both scenarios run
  locally with the standard library. The verifier transport behavior is not a property of the
  repo and comes from the harness.
- Trial conditions: `{"verifier_transport": "fail-twice", "run_date": "2026-09-20"}` (the
  harness fails the verifier call and its one re-send, and runs with that date).
- Run command for the scenario: `PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3`
  (BLOCKER entry); `PYTHONPATH=src python3 -m widget.export - 3` (the MAJOR entry named in the input).

## Schema notes

- Every input above validates structurally against `input.schema.json` as read: `grant`
  requires `item`, `by: "user"`, `channel: "user-turn"`, `turn_ref`, `quoted_words`, `date`;
  `waiver_grant` adds `severity`; `named_items` entries are `item_ref` (location plus claim).
  No case in this lane is about invalid input; every manifest will carry
  `input_validates: true` when `build.py` is written.
- The schema has no field that ties a `reopen` grant to `named_items`; `S2-03` and `S2-06`
  carry the same location and claim in both places.
