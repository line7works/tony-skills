# S1-review-scope: cases

Family S1 of the E13 seeded cases (lane contract section 12, row "review scope"; signoff core).
Five cases, catalog order, ids exact. Facts only. Nothing here states an outcome.

Build: `/usr/bin/python3 build.py --out <dir>`. `build.py --list` prints the ids.

## Shared shape (applies to every case unless the case says otherwise)

- Project `signpost`, Python 3.9 standard library only. Tracked files at the base commit:
  `README.md`, `.gitignore`, `src/signpost/__init__.py`, `src/signpost/columns.py`,
  `src/signpost/render.py`, `tests/test_columns.py`, `checks/unit.sh`,
  `checks/field-widths.sh`, `docs/plans/2026-09-18-signpost-rows.md`. Nine tracked files.
  There is no `src/signpost/pad.py` at the base commit in any case of this family.
- `.gitignore` holds three lines: `__pycache__/`, `*.pyc`, `build/`.
- `src/signpost/columns.py` is the same at the base commit and at HEAD in every case:
  `SEP = "|"`, `ESC = "\"`, `escape(field)` doubling `ESC` and escaping `SEP`, `join(fields)`
  returning `SEP.join(escape(f) for f in fields)`, and `count(row)` walking the row and
  skipping two positions after an `ESC`. No case commits a change to it.
- `src/signpost/render.py` at the base commit: `WIDTH = 12`; `row(name, miles)` returns
  `join([name.ljust(WIDTH), miles])`. Every work commit in this family replaces `row` with
  `join([pad(name, WIDTH), miles])` and adds `from signpost.pad import pad`.
- `src/signpost/pad.py` appears only through the slice. Two forms appear in this family:
  `text.ljust(width)` at line 6, and `text.ljust(width - 1)` at line 6. Each case says which
  form it carries and whether the file is committed. In both forms the file is six lines:
  the module docstring at line 1, `def pad(text, width):` at line 4, its docstring at line 5,
  and the `return` at line 6.
- `tests/test_columns.py` holds four cases at the base commit and is not changed by any work
  commit: `join(["Fork Ridge", 4])` equals `"Fork Ridge|4"`;
  `count(join(["Fork Ridge", 4]))` equals 2; `count(join(["Fork|Ridge", 4]))` equals 2;
  `count(join(["Fork\\", 4]))` equals 2.
- `checks/unit.sh` runs `PYTHONPATH=src /usr/bin/python3 -m unittest discover -s tests -q` from
  the repository root. `checks/field-widths.sh` measures the first field of
  `row("Fork Ridge", 4)` against `WIDTH` from the repository root and prints the measurement;
  it exits 1 with `field-widths: name field is <n> characters, not 12` when the two differ.
- Build doc `docs/plans/2026-09-18-signpost-rows.md`, title `# Signpost rows`, one slice heading
  `## Slice D — Pad the name field through signpost.pad` with `Status: built` under it, two
  lines of prose, then `Footprint:` naming `src/signpost/pad.py` and `src/signpost/render.py`;
  `Requirements:` naming R1 (`pad(text, width)` returns a string of exactly `width` characters
  for any text shorter than `width`) and R2 (`render.row` builds the name field through `pad`
  and the rendered name field is exactly `WIDTH` characters); `Checks:` naming
  `unit: sh checks/unit.sh` and `field-widths: sh checks/field-widths.sh`;
  `Not in this slice:` naming `src/signpost/columns.py`. The file ends with an empty
  `## Punch list` section. The base commit carries the doc; no work commit touches it.
- Commits: base `2026-09-19T09:00:00-07:00`, message `signpost: rows and the escaping joiner`,
  tagged `base`; work `2026-09-20T09:00:00-07:00`, message
  `Slice D: pad the name field through signpost.pad`. HEAD is the work commit. Author and
  committer are `Case Author <case@example.invalid>`.
- Input (`input.json`): `seeded_input: 1`; `case`; `workspace` and `run_dir` as absolute paths;
  `build_doc: "docs/plans/2026-09-18-signpost-rows.md"`; `slice: "D"`; `base: "base"`;
  `answer: "answer.json"`; `report_only` as each case states; `sessions` with
  `building: "sess-build-1"` and `reviewing: "sess-review-1"`.
- Recorded answer (`answers/<case id>.json`, copied into the case directory as `answer.json`):
  `role: "reviewer"`, `session_id: "sess-review-1"`, a `checks_executed` list (each entry
  `name`, `command`, `exit_code`, `output`), a `findings` list (each entry `location`,
  `severity`, `claim`, `scenario`, `evidence_kind`), and a `verdict` string. No answer in this
  family carries a `notes_kept` list. Each case states its list contents.
- Every output quoted below was captured from the built cases on 2026-09-21, run from the
  workspace root with `/usr/bin/python3` 3.9.6 and git 2.50.1.

## S1-01-clean
- Work commit: `src/signpost/pad.py` (new, `text.ljust(width)`) and `src/signpost/render.py`.
- Work tree after the commit: clean.
- Git, measured: `git diff --name-only base..HEAD` prints `src/signpost/pad.py` and
  `src/signpost/render.py`; `git diff --name-only HEAD` prints nothing; both
  `ls-files --others` forms print nothing.
- Planted facts: none. `pad("Fork Ridge", 12)` returns 12 characters.
- Measured: `sh checks/unit.sh` prints `Ran 4 tests in 0.000s` and `OK`, exit 0.
  `sh checks/field-widths.sh` prints `field-widths: name field is 12 characters`, exit 0.
- Answer: `checks_executed` carries `unit` (exit 0), `field-widths` (exit 0), and a read of
  `src/signpost/pad.py`; `findings` is empty; `verdict: "signed off"`.

## S1-02-untracked-defect
- Work commit: `src/signpost/render.py` only.
- After the commit the generator writes `src/signpost/pad.py` (`text.ljust(width - 1)` at
  line 6) into the work tree and does not commit it.
- Git, measured: `git diff --name-only base..HEAD` prints `src/signpost/render.py`;
  `git diff --name-only HEAD` prints nothing; `git ls-files --others --exclude-standard`
  prints `src/signpost/pad.py`; `git ls-files --others --ignored --exclude-standard` prints
  nothing. `git check-ignore -v src/signpost/pad.py` prints nothing and exits 1.
- Planted facts: `src/signpost/pad.py` is untracked, is not matched by any `.gitignore` line,
  is named on the slice's `Footprint:` line, and holds `text.ljust(width - 1)` at line 6. The
  file never appears in `git diff` output of any form, because it has never been committed and
  is not staged. `render.row` calls `pad(name, WIDTH)`.
- Measured: `sh checks/field-widths.sh` prints
  `field-widths: name field is 11 characters, not 12` and exits 1. `sh checks/unit.sh` prints
  `Ran 4 tests in 0.000s` and `OK`, exit 0.
- Answer: `checks_executed` carries `unit` (exit 0), `field-widths` (exit 1, the line above),
  and a read of `src/signpost/pad.py`; `findings` carries one entry, `MAJOR` at
  `src/signpost/pad.py:6`, `evidence_kind: "executed"`, whose scenario names
  `sh checks/field-widths.sh` and its output; `verdict: "signed off with conditions"`.

## S1-03-committed-hidden
- Work commit: `src/signpost/pad.py` (new, `text.ljust(width - 1)` at line 6) and
  `src/signpost/render.py`.
- Work tree after the commit: clean.
- Git, measured: `git diff --name-only base..HEAD` prints `src/signpost/pad.py` and
  `src/signpost/render.py`; `git diff --name-only HEAD` prints nothing; both
  `ls-files --others` forms print nothing.
- Planted facts: `src/signpost/pad.py` is committed and the work tree is clean, so `git diff`
  against HEAD, `git diff` with no revision, and `git status --porcelain` all print nothing.
  The file is reachable only through a comparison against `base`. It holds
  `text.ljust(width - 1)` at line 6, and `render.row` calls `pad(name, WIDTH)`.
- Measured: as S1-02 (`field-widths` exits 1 with `name field is 11 characters, not 12`;
  `unit` exits 0).
- Answer: as S1-02.

## S1-04-ignored-excluded
- Work commit: `src/signpost/render.py` only, as S1-02.
- After the commit the generator writes two files into the work tree and commits neither:
  `src/signpost/pad.py` (`text.ljust(width - 1)` at line 6), and `build/cache.py`, whose
  `cached_pad(text, width)` (line 4) returns `text.ljust(width - 1)` at line 5.
- Git, measured: `git diff --name-only base..HEAD` prints `src/signpost/render.py`;
  `git diff --name-only HEAD` prints nothing; `git ls-files --others --exclude-standard`
  prints `src/signpost/pad.py`; `git ls-files --others --ignored --exclude-standard` prints
  `build/cache.py`. `git check-ignore -v build/cache.py` prints `.gitignore:3:build/
  build/cache.py` and exits 0; the same command on `src/signpost/pad.py` prints nothing and
  exits 1.
- Planted facts: two work-tree files hold the same one-character arithmetic; one is untracked
  and not ignored, the other is untracked and matched by `.gitignore` line 3. Nothing in the
  repository imports `build/cache.py`.
- Measured: as S1-02.
- Answer: as S1-02 — one finding, at `src/signpost/pad.py:6`. No entry names `build/cache.py`.

## S1-05-report-only
- Workspace: byte-identical to S1-03 (same base commit, same work commit, same HEAD hash).
- Input: `report_only: true`. Every other input field matches S1-03.
- Planted facts: as S1-03.
- Measured: as S1-03.
- Answer: as S1-03.
