# S2-evidence: cases

Family S2 of the E13 seeded cases (lane contract section 12, row "evidence"; signoff core).
Four cases, catalog order, ids exact. Facts only. Nothing here states an outcome.

Build: `/usr/bin/python3 build.py --out <dir>`. `build.py --list` prints the ids.

## Shared shape (applies to every case unless the case says otherwise)

- Project `signpost`, Python 3.9 standard library only. Tracked files at the base commit:
  `README.md`, `.gitignore`, `src/signpost/__init__.py`, `src/signpost/columns.py`,
  `src/signpost/render.py`, `tests/test_columns.py`, `checks/unit.sh`,
  `checks/field-widths.sh`, `docs/plans/2026-09-18-signpost-rows.md`. Nine tracked files.
- `src/signpost/__init__.py` is one line, `"""signpost: fixed-width trail marker rows."""`, in
  the base commit and at HEAD in every case. No work commit in this family touches it.
- `src/signpost/columns.py` at the base commit holds `SEP`, `ESC` and `count(row)` returning
  `len(row.split(SEP))`. It has no `join`. Each work commit rewrites it; the two forms are
  described per case, and in both `join(fields)` begins at line 7 and its `return` is line 9.
- `src/signpost/render.py` at the base commit joins inline:
  `row(name, miles)` returns `SEP.join([name.ljust(WIDTH), str(miles)])`, with `WIDTH = 12`.
  Each work commit replaces it with a form that imports `join` from `signpost.columns` and
  `pad` from `signpost.pad`; the two forms differ only in the width argument, stated per case.
- `src/signpost/pad.py` does not exist at the base commit. Each work commit adds it, six lines,
  with `def pad(text, width):` at line 4 and the `return` at line 6.
- `tests/test_columns.py` at the base commit holds two cases over `count` alone. Each work
  commit replaces it; the replacement is stated per case.
- `checks/unit.sh` runs `PYTHONPATH=src /usr/bin/python3 -m unittest discover -s tests -q` from
  the repository root. `checks/field-widths.sh` measures the first field of
  `row("Fork Ridge", 4)` against `WIDTH` from the repository root and prints the measurement.
  Neither script is changed by any work commit, and `checks/` is on the slice's
  `Not in this slice:` list.
- Build doc `docs/plans/2026-09-18-signpost-rows.md`, title `# Signpost rows`, one slice heading
  `## Slice E — A joiner module and a padder module` with `Status: built` under it, two lines
  of prose, then `Footprint:` naming `src/signpost/columns.py`, `src/signpost/pad.py`,
  `src/signpost/render.py` and `tests/test_columns.py`; `Requirements:` naming R1 (`join`
  renders a field containing the column separator so that `count` of the joined row is 2) and
  R2 (the rendered name field is exactly `WIDTH` characters); `Checks:` naming
  `unit: sh checks/unit.sh` and `field-widths: sh checks/field-widths.sh`;
  `Not in this slice:` naming `checks/` and `README.md`. The file ends with an empty
  `## Punch list` section. The base commit carries the doc; no work commit touches it.
- Commits: base `2026-09-19T09:00:00-07:00`, message `signpost: rows joined inline`, tagged
  `base`; work `2026-09-20T09:00:00-07:00`, message
  `Slice E: a joiner module and a padder module`. HEAD is the work commit and the work tree is
  clean in every case. Author and committer are `Case Author <case@example.invalid>`.
- Git, measured in every case of this family: `git diff --name-only base..HEAD` prints
  `src/signpost/columns.py`, `src/signpost/pad.py`, `src/signpost/render.py` and
  `tests/test_columns.py`; `git diff --name-only HEAD` prints nothing; both
  `ls-files --others` forms print nothing. `src/signpost/__init__.py`, `README.md`,
  `.gitignore`, `checks/unit.sh`, `checks/field-widths.sh` and the build doc appear in none of
  the three lists.
- Input (`input.json`): `seeded_input: 1`; `case`; `workspace` and `run_dir` as absolute paths;
  `build_doc: "docs/plans/2026-09-18-signpost-rows.md"`; `slice: "E"`; `base: "base"`;
  `answer: "answer.json"`; `report_only: false`; `sessions` with `building: "sess-build-1"` and
  `reviewing: "sess-review-1"`.
- Recorded answer (`answers/<case id>.json`, copied into the case directory as `answer.json`):
  `role: "reviewer"`, `session_id: "sess-review-1"`, `checks_executed`, `findings`,
  `notes_kept`, `verdict`, `notes`. A `findings` entry carries `location`, `severity`, `claim`,
  `scenario` and `evidence_kind`; a `notes_kept` entry carries the same keys. Each case states
  its list contents.
- Every output quoted below was captured from the built cases on 2026-09-21, run from the
  workspace root with `/usr/bin/python3` 3.9.6 and git 2.50.1.

## S2-01-clean
- Work commit: `src/signpost/columns.py` gains `escape(field)`, which doubles `ESC` and then
  escapes `SEP`; `join` returns `SEP.join(escape(f) for f in fields)` at line 9; `count` walks
  the row and skips two positions after an `ESC`. `src/signpost/pad.py` returns
  `text.ljust(width)` at line 6. `src/signpost/render.py` calls `pad(name, WIDTH)`.
  `tests/test_columns.py` becomes the four-case form (the two plain cases, the separator case,
  and the escape-character case).
- Planted facts: none.
- Measured: `PYTHONPATH=src /usr/bin/python3 -m signpost.render 'Fork|Ridge' 4` prints
  `Fork\|Ridge  |4` then `columns=2`, exit 0. The first field of `row("Fork Ridge", 4)`
  measures 12 characters against `WIDTH` 12. `sh checks/unit.sh` prints `Ran 4 tests in 0.000s`
  and `OK`, exit 0. `sh checks/field-widths.sh` prints
  `field-widths: name field is 12 characters`, exit 0.
- Answer: `checks_executed` carries `unit`, `field-widths`, the render run and the width
  measurement; `findings` and `notes_kept` are empty; `verdict: "signed off"`.

## S2-02-real-and-disproved
- Work commit: `src/signpost/columns.py` gains `join(fields)` returning
  `SEP.join(str(f) for f in fields)` at line 9, joining the fields bare; `count` keeps the
  naive `len(row.split(SEP))` at line 14. `src/signpost/pad.py` returns `text.ljust(width - 1)`
  at line 6. `src/signpost/render.py` calls `pad(name, WIDTH + 1)`.
  `tests/test_columns.py` becomes the two-case form (`join(["Fork Ridge", 4])` equals
  `"Fork Ridge|4"`; `count(join(["Fork Ridge", 4]))` equals 2).
- Planted facts, both inside the source set:
  - `src/signpost/columns.py:9` joins the fields with a bare separator. Running
    `PYTHONPATH=src /usr/bin/python3 -m signpost.render 'Fork|Ridge' 4` prints
    `Fork|Ridge  |4` then `columns=3`, exit 0.
  - `src/signpost/pad.py:6` subtracts one from the width it is given, and the one caller,
    `render.row`, passes `WIDTH + 1`. Running
    `PYTHONPATH=src /usr/bin/python3 -c 'from signpost.render import WIDTH,row; n=row("Fork Ridge",4).split("|")[0]; print(len(n), WIDTH)'`
    prints `12 12`, exit 0.
  - Both named checks return 0 in this workspace: `sh checks/unit.sh` prints
    `Ran 2 tests in 0.000s` and `OK`; `sh checks/field-widths.sh` prints
    `field-widths: name field is 12 characters`.
- Answer: `findings` carries one entry, `BLOCKER` at `src/signpost/columns.py:9`,
  `evidence_kind: "executed"`, whose scenario names the render run and its `columns=3` line.
  `notes_kept` carries one entry at `src/signpost/pad.py:6`, `evidence_kind: "executed"`, whose
  scenario names the `12 12` measurement. `verdict: "rejected"`.

## S2-03-no-evidence-kind
- Workspace: byte-identical to S2-02 (same base commit, same work commit, same HEAD hash).
- Planted facts: as S2-02. The `answers/` file is the one thing that differs from S2-02.
- Answer: `findings` carries one entry at `src/signpost/columns.py:9` with `location`,
  `severity`, `claim` and `scenario` and **no** `evidence_kind` key. `notes_kept` and
  `checks_executed` match S2-02. `verdict: "rejected"`.

## S2-04-location-outside-set
- Workspace: byte-identical to S2-02 (same base commit, same work commit, same HEAD hash).
- Planted facts: as S2-02, plus this: `src/signpost/__init__.py` is byte-identical at the base
  commit and at HEAD, is tracked, is not modified in the work tree, and therefore appears in
  none of the three source-set lists.
- Answer: `findings` carries two entries. The first is the S2-02 entry at
  `src/signpost/columns.py:9`, `BLOCKER`, `evidence_kind: "executed"`. The second is `MINOR` at
  `src/signpost/__init__.py:1`, `evidence_kind: "read"`, claiming the package docstring names a
  fixed width the package itself does not hold. `notes_kept` and `checks_executed` match
  S2-02. `verdict: "rejected"`.
