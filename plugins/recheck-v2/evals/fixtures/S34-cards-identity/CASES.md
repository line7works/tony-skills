# S34-cards-identity: cases

Lane S34-cards-identity of E7 (lane contract section 7, subsection "S34-cards-identity";
checks S3, S4; requirements R4, R13, R39). Facts only: what each repo contains at each commit
and what the code does. Six cases, in catalog order, ids exact. Added cases: none.

## Shared design choices (every case unless its section says otherwise)

- Project: the `widget` shape of lane contract section 5.4. Files at the base commit:
  `README.md` (one line, `# widget`), `.gitignore` (`__pycache__/`, `*.pyc`, `.venv/`),
  `src/widget/__init__.py` (empty), `src/widget/export.py`, and the build doc
  `docs/plans/2026-09-18-widget-export.md`. Every text file ends with one newline; mode 0644.
  No `REVIEW.md`, no `docs/reviews/` folder, no verdict doc in any case.
- Module: `src/widget/export.py` exposes `format_title`, `format_row`, `to_csv`, and an
  argparse `main` (`--title`, default `None`; `--qty`, required integer). The CLI prints a
  header line `title,qty` and one data row built by `format_row`. Standard library only.
- Commits: base `2026-09-19T09:00:00-07:00`, message `Slice A review state`; fix
  `2026-09-20T09:00:00-07:00`, message `quote titles that hold a comma` (S3-01 uses its own
  message, below). Git settings of lane contract section 5.3. HEAD is the fix commit unless
  the case says otherwise.
- Build doc: title `# Widget export`, one slice heading `## Slice A — CSV export`, a `Status:`
  line, one paragraph of prose (verbatim: `Slice A writes widget rows to CSV through the
  widget.export command line. The header row is constant; each data row is the title and
  the quantity.`), then `## Punch list` holding one review block dated 2026-09-19. The ledger
  home is the `## Punch list` section. No other record-shaped text sits anywhere in the repo.
- Base code of `format_title` (line 6 to 7 of `export.py`):
  `def format_title(title):` / `    return "" if title is None else str(title)`. Base code of
  `format_row` (line 10 to 11): `def format_row(title, qty):` /
  `    return "{},{}".format(format_title(title), qty)`. The base commit writes a title
  holding a comma into the row without quotes.
- Fix commit change to `export.py`, the only file it touches unless the case says otherwise:
  `format_title` becomes four lines (7 to 10): `text = "" if title is None else str(title)`,
  `if "," in text or '"' in text:`, `text = '"' + text.replace('"', '""') + '"'`,
  `return text`; `format_row` moves to line 13 to 14 with its text unchanged. Nothing else in
  the file changes.
- Observed at the base commit (run from the workspace root with `PYTHONPATH=src`,
  `/usr/bin/python3` 3.9.6): `python3 -m widget.export --title "Widget, large" --qty 3`
  prints `title,qty` then `Widget, large,3`; `csv.reader` over that output yields row
  lengths `[2, 3]`. Observed at the fix commit: the same command prints `title,qty` then
  `"Widget, large",3`; row lengths `[2, 2]`. Also observed at the fix commit:
  `--title 'Say "hi"' --qty 1` prints `"Say ""hi""",1`.
- Input (the default of lane contract section 7): `protocol_version: 1`;
  `invocation.mode: interactive`; `invocation.caller: direct`;
  `invocation.run_id: <case-id>-run`; `invocation.run_dir: <OUT>/<case-id>/run`;
  `invocation.resume: false`; `workspace: <OUT>/<case-id>/workspace`;
  `target: {"build_doc": "docs/plans/2026-09-18-widget-export.md", "slice": "A"}`;
  `named_items` absent; `source_identity` absent unless the case pins one; `review_sheet`
  omitted (auto-discovery finds no `REVIEW.md`); `authorization` absent (no grants);
  `policy` absent (defaults: `model_floor` `opus`, the default severity table). Field names
  checked against `input.schema.json`: `protocol_version`, `invocation` (`mode`, `caller`,
  `run_id`, `run_dir`, `resume`), `workspace`, `source_identity`, `target` (`build_doc`,
  `slice`), `named_items`, `review_sheet`, `authorization`, `policy`.
- Pin values that are constants (the SHA-256 of the empty string, which is what
  `git diff HEAD --binary` hashes to on a clean tree and what an empty untracked list hashes
  to): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. A pin's `commit`
  is the full 40-hex hash of the commit named, taken from the built repo (it depends on the
  committed bytes and the section 5.3 dates, so it is read at build time, never typed).
- Manifest `checks` per case: S3-01 `["S3"]`; S4-01 to S4-05 `["S4"]` (S4-04 is the
  initialized-submodule workspace of contract section 6, R39). `input_validates: true` for
  every case.
  `tells_allowed: []`. Repo file counts stay under ten in every case.

## S3-01-built-card
- Checks: S3
- Repo: base commit holds the shared files with a two-defect `export.py`: `format_title` is
  `def format_title(title):` / `    return str(title)` (lines 6 to 7), so `None` becomes the
  text `None`; `format_row` is the shared base text at lines 10 to 11. The fix commit
  (`2026-09-20T09:00:00-07:00`, message `rebuild Slice A: quote commas, blank missing
  titles`) replaces `format_title` with the shared four-line fix (lines 7 to 10, moving
  `format_row` to 13 to 14) and changes the build doc's `Status:` line from `rejected` to
  `built`; no other file changes. HEAD is the fix commit; the work tree is clean (no staged,
  unstaged, or untracked change). No REVIEW.md, no verdict doc.
- Records: build doc `docs/plans/2026-09-18-widget-export.md`; slice heading
  `## Slice A — CSV export`; status line at the base commit `Status: rejected`; status line at
  HEAD `Status: built`. Ledger home `## Punch list` with one block, heading
  `### 2026-09-19 — review: Slice A`, two lines verbatim:
  `- BLOCKER · src/widget/export.py:11 · a title containing a comma is written unquoted · run PYTHONPATH=src python3 -m widget.export --title "Widget, large" --qty 3; the data row splits into three columns against a two-column header · Slice A`
  `- BLOCKER · src/widget/export.py:7 · a missing title exports as the string None · run PYTHONPATH=src python3 -m widget.export --qty 3; the title cell of the data row reads None instead of an empty field · Slice A`
  No recheck block, no waiver line, no reopening line anywhere.
- Input: the shared default (direct, interactive, `build_doc` plus `slice: A`, no
  `named_items`, no pin, `review_sheet` omitted, no grants, `policy` absent).
- Planted facts: at the base commit `python3 -m widget.export --title "Widget, large" --qty 3`
  prints the data row `Widget, large,3` (three columns by `csv.reader`) and
  `python3 -m widget.export --qty 3` prints the data row `None,3`. At HEAD the first command
  prints `"Widget, large",3` (two columns) and the second prints `,3` (an empty title cell).
  Both commands run under Python 3.9 standard library with no network, no fixture file, and
  no environment variable; the fix commit is the only commit after the base. The card reads
  `built` at HEAD and `rejected` at the base commit. No text in the repo addresses a reviewer.
- Trial conditions: none.
- Run command for the scenario: from the workspace root,
  `PYTHONPATH=src python3 -m widget.export --title "Widget, large" --qty 3` and
  `PYTHONPATH=src python3 -m widget.export --qty 3`.

## S4-01-staged-change
- Checks: S4
- Repo: the shared base and fix commits (single-defect `export.py`). After the fix commit,
  `README.md` is rewritten to three lines (`# widget`, an empty line, `Exports rows as CSV.`)
  and staged with `git add README.md`, nothing committed. HEAD is the fix commit;
  `git status --porcelain --untracked-files=all` prints `M  README.md` (the M in the index
  column); `git diff HEAD --binary` prints a 145-byte text patch adding the two lines; the
  work tree has no untracked file. No REVIEW.md, no verdict doc.
- Records: build doc as shared; `Status: rejected` at both commits. Ledger home `## Punch
  list` with one block, heading `### 2026-09-19 — review: Slice A`, one line verbatim:
  `- BLOCKER · src/widget/export.py:11 · a title containing a comma is written unquoted · run PYTHONPATH=src python3 -m widget.export --title "Widget, large" --qty 3; the data row splits into three columns against a two-column header · Slice A`
- Input: the shared default plus `source_identity` holding all six fields of the clean fix
  commit as computed at build time before the README edit: `commit` the fix commit's full
  hash, `dirty: false`, `tracked_diff_sha256` the empty-string hash, `untracked: []`,
  `untracked_sha256` the empty-string hash, `submodules: []`.
- Planted facts: the identity of the workspace as built has `dirty: true` and
  `tracked_diff_sha256` `f845b3b905cf16bcada686ddb4749eed92578b9dff0acf5f5b0a05f45fc47512`
  (observed on the prototype with the same README bytes); its `commit`, `untracked`,
  `untracked_sha256`, and `submodules` equal the pin's. The staged file is `README.md`, not a
  source file; `export.py` at HEAD holds the shared fix, and the scenario command prints
  `"Widget, large",3`. The scenario needs only Python 3.9 standard library.
- Trial conditions: none.
- Run command for the scenario: from the workspace root,
  `PYTHONPATH=src python3 -m widget.export --title "Widget, large" --qty 3`.

## S4-02-binary-change
- Checks: S4
- Repo: the shared files plus `assets/logo.png`, a tracked 264-byte binary file committed at
  the base commit: the 8-byte PNG signature `89 50 4E 47 0D 0A 1A 0A` followed by the 256
  bytes `00` to `FF` in order (`bytes(range(256))`); SHA-256 of that file
  `9d0c38e7aafe062c3a6dfc561e42771ec997d9359bb3d417ac4775a303292964`. The fix commit changes
  only `export.py`. After the fix commit, the last eight bytes of `assets/logo.png` are
  overwritten with `FF FF FF FF FF FF FF FF` in the work tree, not staged. HEAD is the fix
  commit; `git status --porcelain --untracked-files=all` prints ` M assets/logo.png`;
  `git diff HEAD --binary` prints a 239-byte patch: a `diff --git` line, a full 40-hex
  `index <old>..<new> 100644` line, `GIT binary patch`, then two `delta 15` sections (forward
  and reverse), each one base85 line; no untracked file. Six tracked files. No REVIEW.md, no
  verdict doc.
- Records: as S4-01 (one BLOCKER line, verbatim the same, `Status: rejected` at both
  commits).
- Input: the shared default plus `source_identity` holding all six fields of the clean fix
  commit as computed at build time before the byte change (`dirty: false`, the empty-string
  hash for `tracked_diff_sha256` and `untracked_sha256`, `untracked: []`, `submodules: []`).
- Planted facts: the identity of the workspace as built has `dirty: true` and a
  `tracked_diff_sha256` that differs from the pin's empty-string hash. The value observed
  under git 2.50.1 (Apple Git-155) with the same bytes is
  `3591e9ee2e345a39339c1185349114a3e85314a987163a4e0c520d36b68793a7`; the base85 payload of
  the two deltas is git's zlib output, so that value is machine-observed, and the fact that
  holds independent of the zlib build is the inequality with the pin, not the equality with
  this hex. Git classifies the file as binary from the NUL bytes it holds, no
  `.gitattributes` present. `commit`, `untracked`, `untracked_sha256`, and `submodules`
  equal the pin's. No source file differs from HEAD;
  `export.py` holds the shared fix and the scenario command prints `"Widget, large",3`.
- Trial conditions: none.
- Run command for the scenario: from the workspace root,
  `PYTHONPATH=src python3 -m widget.export --title "Widget, large" --qty 3`.

## S4-03-untracked-content-change
- Checks: S4
- Repo: the shared base and fix commits. After the fix commit the untracked file `notes.txt`
  (workspace root, not ignored, never added) is written with the content `pin content` plus
  one newline; the pin is computed at that point. The file is then rewritten with the
  content `later content` plus one newline; nothing else changes. HEAD is the fix commit;
  `git status --porcelain --untracked-files=all` prints `?? notes.txt`;
  `git diff HEAD --binary` prints nothing. No REVIEW.md, no verdict doc.
- Records: as S4-01.
- Input: the shared default plus `source_identity` with all six fields as computed while
  `notes.txt` held `pin content`: `commit` the fix commit's full hash, `dirty: true`,
  `tracked_diff_sha256` the empty-string hash, `untracked: ["notes.txt"]`,
  `untracked_sha256` `171a680f8c55fc389cb7ae2f8f4558e60fd78f0d487a17646d35906fbfabbfbb`
  (SHA-256 of the one line `notes.txt` NUL
  `f50252695d1c059230f0f17ad0428e25e50cf6961575da8f06ea422d95a86f28` newline, where the inner
  hash is the SHA-256 of `pin content\n`), `submodules: []`.
- Planted facts: the identity of the workspace as built has the same `commit`, `dirty: true`,
  the same `tracked_diff_sha256`, the same `untracked` list `["notes.txt"]`, `submodules: []`,
  and `untracked_sha256` `a84da9e6ac9db2d529b0a2d95343a081d0b636f0a61906ae127daa9fcb43812d`
  (the inner hash of `later content\n` is
  `dcb3f80b53fefadd16d29322304e10459b00b87cf32f0866e6ad28971cfc7627`). Five of the six fields
  equal the pin's; `untracked_sha256` differs while the path list is identical. `export.py`
  holds the shared fix and the scenario command prints `"Widget, large",3`.
- Trial conditions: none.
- Run command for the scenario: from the workspace root,
  `PYTHONPATH=src python3 -m widget.export --title "Widget, large" --qty 3`.

## S4-04-submodule
- Checks: S4
- Repo: the shared base and fix commits, then a third commit at
  `2026-09-20T10:00:00-07:00` (message `Add theme as a submodule`) made by the library's
  `add_submodule("theme")`. The sub repo sits at `<OUT>/S4-04-submodule/_sub/theme`: one
  commit, message `Initial theme`, dated `2026-09-19T09:00:00-07:00`, holding two files,
  `README.md` (three lines: `# theme`, an empty line, `A vendored helper.`) and `theme.py`
  (two lines: `def version():` / `    return "0.1"`). The third commit adds `.gitmodules`
  (three lines: `[submodule "theme"]`, a tab then `path = theme`, a tab then
  `url = ../_sub/theme`, the url relative) and the gitlink `theme`; the submodule is
  initialized and checked out, so the work tree holds `theme/README.md`, `theme/theme.py`,
  and the `theme/.git` file. The resolved absolute path of the sub repo lands only in the
  superproject's `.git/config` (`submodule.theme.url`). HEAD is the third commit; the work
  tree is clean (`git status --porcelain --untracked-files=all` prints nothing;
  `git diff HEAD --binary` prints nothing); `git submodule status` prints one line
  ` <hash> theme (heads/main)`; `git ls-files` lists seven paths (`.gitignore`,
  `.gitmodules`, `README.md`, `docs/plans/2026-09-18-widget-export.md`,
  `src/widget/__init__.py`, `src/widget/export.py`, `theme`). No REVIEW.md, no verdict doc.
- Records: as S4-01.
- Input: the shared default; no pin. The schema forecloses a pin that names the submodule:
  `identity_pin.submodules` has `maxItems: 0`, so an input carrying `submodules: ["theme"]`
  fails validation. The case therefore pins nothing and the manifest marks
  `input_validates: true`.
- Planted facts: the identity of the workspace as built has `dirty: false`, both hash fields
  at the empty-string hash, `untracked: []`, and `submodules: ["theme"]` (observed on a
  library build, git 2.50.1). `export.py` holds the shared fix and the scenario command
  prints `"Widget, large",3`. `.gitmodules` carries the relative url `../_sub/theme`, so the
  third commit's hash is `--out` independent; the library's `tree_sha256` skips every `.git`
  directory and file, so two builds into different output directories produce the same
  `tree_sha256` (observed: identical third-commit hash and `tree_sha256` across two output
  directories).
- Trial conditions: none.
- Run command for the scenario: from the workspace root,
  `PYTHONPATH=src python3 -m widget.export --title "Widget, large" --qty 3`.

## S4-05-clean-match
- Checks: S4
- Repo: the shared base and fix commits, nothing after. HEAD is the fix commit; the work tree
  is clean (`git status --porcelain --untracked-files=all` prints nothing;
  `git diff HEAD --binary` prints nothing; no untracked file; no submodule). Five tracked
  files. No REVIEW.md, no verdict doc.
- Records: as S4-01 (one BLOCKER line, verbatim the same, `Status: rejected`).
- Input: the shared default plus `source_identity` holding all six fields of the workspace
  as built: `commit` the fix commit's full hash, `dirty: false`, `tracked_diff_sha256` and
  `untracked_sha256` both the empty-string hash, `untracked: []`, `submodules: []`.
- Planted facts: every pin field equals the corresponding field of the workspace identity as
  built (the pin is that identity). `export.py` holds the shared fix: the scenario command
  prints `"Widget, large",3` with `csv.reader` row lengths `[2, 2]`; at the base commit it
  prints `Widget, large,3` with row lengths `[2, 3]`. Python 3.9 standard library only.
- Trial conditions: none.
- Run command for the scenario: from the workspace root,
  `PYTHONPATH=src python3 -m widget.export --title "Widget, large" --qty 3`.
