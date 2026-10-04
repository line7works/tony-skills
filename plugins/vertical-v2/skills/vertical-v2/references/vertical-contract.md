# Vertical v2 core: behavioral contract

What this station does, what it reads, what it may write, what stops it, and the words it uses for a
state. Written for E15 slice 1 of the skills v2 rebuild, against the E15 lane contract (sections 6 and
8, amendments A1 to A17) and the control room's readings CR-1 to CR-10 in the slice 1a brief, as the
slice 1a fix round applied A3 (C1A-1 to C1A-9), the design round applied A4 (the one packet builder,
the local receipt, B5, C1A2-1 to C1A2-5), and fix round 3 applied A5 (the readers root by allowlist
identity, this core's own fence reader, C1A3-3 to C1A3-6) and A7 (the gate reads with that fence reader),
fix round 4 applied A8 (strict plain code blocks, C1A4-1; `readers.py --version` isolated, C1A4-2; the
removal of copies never follows a link, C1A4-3), and fix round 5 applied A9 (no raw HTML lines, C1A5-1 and
C1A5-2; a `summons` folder that is a link refuses, C1A5-3; a `packets` link is removed as a link, C1A5-4), and
fix round 6 applied A10 and A11 (exact labels with A11's six values, C1A6-1; a `packets` entry that is not a
real folder is removed unopened, C1A6-2), fix round 7 applied A12 (plain structure only, C1A7-1; the run files,
C1A7-2), fix round 8 applied A13 (two readings: the line rules and a vendored CommonMark reader must take every
decision from the doc the same way), fix round 9 applied A14 and A15 (the label bug, three near misses, hidden labels),
fix round 10 applied A16 (a character allowlist, folded label and heading-name tests, folded withheld names), and fix
round 11 applied A17 (the fold drops the marks of accented letters, refusal (b) sets aside leading punctuation, wider
withheld names, notes headings read with spaces). Where this
document and that contract differ, the contract is the authority and this document is the defect.
`references/back-loop.md` is the discipline the three back cores share; this document is this core's own.

Contents: 1 Job · 2 What is kept and what moved · 3 The phases · 4 The input · 5 The base, the scope and
the copies · 6 The review mechanics · 7 Stops and exits · 8 The load-bearing forms · 9 The result ·
10 The records component · 11 The trace · 12 The harness seams · 13 The seeded families · 14 What this
core never does · 15 Interface.

## 1. Job

Every slice of a build has been signed off. Before the build is called done, the whole vertical is
reviewed against its base: fresh local reviewers at full scope, joined on the owner's word in this run
by outside reviewers under a mandate to reject it; every outside finding is verified against the source
before it lands; one verdict doc comes out. Nothing is fixed here.

The script never judges code, a finding or a slice (ruling E15-4). It validates the input, finds the
build doc, reads the cards and the records, computes the base and the boundary, cuts the review copies,
builds the packets and their lists, builds the readers requests, holds the executor's recorded answers to
the run, merges and counts, renders and parses the forms, writes the trace and the verdict doc, and
validates the result. The judging is the reviewers' and the executor's, recorded with who concluded it:
the readers call id and row on every finding, the executor's stamp and re-grade reasons beside it.

## 2. What is kept and what moved

Kept from v1 (ruling E15-1): the gate (every slice `signed off`, malformed input never passes, the
collapse only by the owner's words, recorded); the two preconditions (git, the tree clean where the
review looks); the ask every run, in v1's suggest order, waiting for an answer that names its rows;
the base precedence; the tracked-files-only export with the review records left out; the local review
first and independent; survivors continue (a named outside row that is dropped is recorded with its
status and reason and the run goes on with the others); every outside finding verified; `Refuted: N`;
re-gradings recorded with a reason;
the repeats and misses against the record; the one write, appended on a rerun; the stop at the verdict;
the `VERTICAL:` block. The reviewer eligibility, counts and test requirements are v1's (owner pick P6):
the local fleet at the Opus floor, the lenses the depth and the inspection sheet select, the outside
rows the owner names.

What moved: the deterministic half is a script; the review mechanics v1 held by deference are stated in
section 6 in this core's own words (ruling E15-6), and the lens briefs in `references/lens-briefs.md`;
the local lenses review a copy of the reviewed commit with no history instead of a detached worktree (A2,
Q1); every reviewer workspace and packet is cut by one function from the reviewed commit only, fresh for
every summons, under one allow rule (A4; section 5), its spec has the ledger and the builder's working
records removed, and it carries a hashed file list and a withheld list (ruling E15-8, widened by A3); the
local verdict is fixed by a receipt that `request --outside` holds the run to (A4; sections 3.5, 3.6); the cards come
from the records component as well as the `Status:` lines (ruling E15-9); every reader summons is a
trace line (ruling E15-7); the build doc is read twice, by this core's line rules and by a vendored CommonMark
reader, and a decision the two take differently stops the run (A13; section 5, "Two readings").

## 3. The phases

A phase command against a run at the wrong phase is exit 2 naming the command to run instead. Every
phase reads and writes only the run directory, except `verdict`'s one write.

**The run files** (A12, C1A7-2). Every run file this core reads or opens itself (`gate.json`, `ask.json`,
`scope.json`, `requests-local.json`, `requests-outside.json`, `local.json`, `local-receipt.json`,
`outside.json`, `verdict.json`, `selection-build.json`, each readers sidecar and capture, a recorded raw file,
`trace.jsonl` before the trace module reads it or appends to it) is checked before anything opens the path:
a link, anything that is not a regular file (a named pipe, a socket, a folder) or a path whose real location
lies outside the run directory is refused, named, with the run's existing refusal for a damaged run directory:
exit 1 where an artifact the phase needs cannot be read (the run artifact named, nothing written), exit 5 where
the local review's record is held to its receipt (`record-local`, `request --outside`, `verdict`). A present
artifact is never read as absent, and a planted pipe never hangs a phase. The frame's own reads of
`checkpoint.json` and `input.json` (`station_core/driver.py`, a back-frame copy) are not covered here: they join
the E15 punch list.

### 3.1 `gate --run-dir D [--doc PATH | --name NAME] [--records-root DIR]`

The doc hunt (ruling E15-10, `station_core/hunt.py`): `--doc` takes the build doc the invocation names
or the plan the session established (an existing `.md` inside the workspace; anything else is refused,
exit 5); else the repo's tiers, lowest tier deciding: `docs/plans/*-<name>.md` and `docs/plans/<name>.md`,
then `docs/<name>-build-plan.md`, then a phase or slice doc (`docs/*phase*.md`, `docs/*slice*.md`,
`plan/*.md`). `none` stops (`selection-none`, ask the owner); `several` stops (`selection-several`, the
candidates listed, none picked).

The slices: every `## Slice <name> <dash> <short>` heading (the build-doc form's slice pattern) and the
one exact `Status:` label inside its section (A10; section 5, "Exact labels"), read outside fences under this
core's one fence rule (A7, A8; section 5, "The fence rule"), never the frame's parse: a heading or a label
inside a fence is content, never a slice or a card. A build doc holding any fence line the rule does not
accept, any raw HTML line (A9; section 5, "No raw HTML lines": a label inside an HTML comment is never a
card), or any `Status:` line in a slice or `Base:` line in the header that the label rule does not take (A10,
C1A6-1: not exact, not the last line of its paragraph, or a second one; a label held hidden in a link title, a
link reference definition or an inline comment is never a card), or any heading or label line off the plain
form (A12, C1A7-1; section 5, "Plain structure": indented, after a list-item or block-quote marker, or a
heading whose `#`s are not followed by exactly one space), or any character outside the character list outside an
accepted fence (A16; section 5, "The character list": named by its code point) stops the gate (`doc-unreadable`,
naming the line, both lines for a second label) before the ask; so does a doc whose slices, cards, recorded base or
withheld sections a CommonMark reader takes differently from those line rules, or that the CommonMark reading refuses
(A14: a rendered label line in a paragraph it cannot map to source lines, a level 1 or 2 heading off the slice form
that starts with "slice", a heading that starts like a `Status:` or `Base:` label; A16: a rendered character outside
the list), and, once the workspace is known to be a git work tree, another Markdown file of HEAD that a CommonMark
reader declares the builder's notes and the line reading does not (A13, A14; section 5, "Two readings": the first line
where they differ is named, with the decision); a file one of whose heading lines holds a character outside the list
is withheld and named, never a stop (A16 (2)); when the records component's importer reads a
card from a fenced literal, the card-and-line comparison below stops the run (`card-disagrees`). Zero
slices, or a slice with no `Status:` line, stops (`gate-malformed`); a collapse never passes either.

The cards (reading CR-1): the records component's `state` for the build doc. A slice's card is its
`card_observed` (the last card set or observed in the log); it must equal the slice's `Status:` line
text, and a disagreement stops (`card-disagrees`), naming the records' card and the line. The
component's `card_derived` is recorded beside it in `gate.json` and never stops the gate (the owner's
ruling, E15 lane contract A3, C1A-2: v1's gate reads the card, not a derivation): a slice whose derived
card differs from its observed card (an open finding in the log behind a signed card) is named in the
verdict's Method line with both cards. A slice the log names nothing about falls back to its `Status:`
line, and `gate.json`'s notes say so. Every slice must stand `signed off`; a short slice stops (`gate-short`), naming each slice and its
state (a `built` card's remedy is a fresh slice signoff, never a recheck), unless the input carries the
owner's `collapse_gate` words, which are recorded with the short slices and printed in the Method line.

The preconditions, before the ask: the workspace is a git work tree root with a commit (else `not-git`);
the base (section 5); the boundary, `git diff --name-status <base>..HEAD`; the tree, `git status
--porcelain`: dirt touching a boundary file or the build doc stops (`dirty-boundary`, naming the paths)
unless the input carries the owner's `committed_only` words; dirt elsewhere is listed and the review
proceeds on HEAD. Writes `gate.json` (and `selection-build.json` from a hunt).

### 3.2 `ask --run-dir D [...]`

Three modes. With no file: the two `suggest` argv lists, in v1's order: the local row alone with
`--floor opus`, then `gpt-astra,gpt-sol,gemini,deepseek,qwen` with no floor, both with `--run <run id>
--run-dir <run dir>/readers`. With `--local-suggest F --outside-suggest G`: suggest's own outputs, each
for this run (exit 5 otherwise), the local one under the floor and the outside one under none, every row
present; the ask is rendered (v1's question, then one line per row with the model suggest showed, the
profile it runs under, and any drop note) into `ask.json`. With `--answer FILE` (kind `ask`,
`references/answer.schema.json`): the rows the owner's words name and his words, verbatim, for this run
only (exit 5 for another run's). Nothing after the ask runs until the answer is recorded.

The roster is read through section 11's preflight, so a readers root that is not the expected readers
plugin by identity, a v1 root among them, stops the run (`station-refused`) before any of its files is
opened. The local row is `claude-session` (profile `repo-with-tools`) on Claude
Code and `claude-opus-cli` on Codex, with the profile that row offers (section 12). The outside rows read the export as a workspace
(`repo`) where the row offers it, and a packet otherwise (`packet-only`).

### 3.3 `scope --run-dir D`

The packets (ruling E15-8 as A4 reads it; section 5 is their one rule): one per local lens
(`packets/local-<lens>/`) and one per outside row the answer named (`packets/outside-<row>/`, a named row
suggest dropped included; it is never sent). `scope` reads the reviewed commit (the one `gate.json`
records) once, takes the inspection sheet from it (never from the working tree), sets the lenses from the
depth and that sheet, records the working tree's untracked, ignored and changed names (names only), and
cuts each packet once through the packet builder as a preview, so the executor can see what each reviewer
will receive: its material, `files.json` (every file, its size and sha256) and `withheld.json` (everything
left out, named with why). No request ever points at a preview. Each packet's fingerprint (`digest`: its
file list, its withheld list and its left-out list) goes into `scope.json`, with `staged_names` mapping
every packet-only staged name back to its path, so a finding at a staged name reads back to the right
file. The outside mandate is `assets/vertical-mandate.md`, v1's byte for byte, its three slots filled: the
spec, the base commit, the boundary lines. Each local mandate is the lens's brief, the scope, the base and
boundary, the ledger-versus-spec line, the repo's checks, and the reporting shape; its words follow the
local row's profile (C1A-9): under `repo-with-tools` the lens may run the project's tests in its copy;
under `repo` it says the lens runs nothing, reads the code, and reports a check it would have run as not
executed, and it promises no test run. A reviewed commit's build doc holding any fence line the fence
rule does not accept (section 5, "The fence rule"), any raw HTML line (section 5, "No raw HTML lines"), or any
label line the label rule does not take (section 5, "Exact labels"), or any heading or label line off the plain
form (section 5, "Plain structure"), or any character outside the character list (section 5, "The character
list"), or any decision a CommonMark reader takes differently from those line rules or any of its four refusals, the
builder's-notes declaration of another Markdown file of the commit included (section 5, "Two readings"),
stops the run here (`doc-unreadable`, naming the line) before any packet is built. A `packets` entry that is not a real folder (a link, a plain
file, a named pipe, a socket) is removed as itself with `os.unlink`, never followed and never opened, before
the previews are cut (C1A5-4, C1A6-2). Writes `scope.json` and `packets/`.

### 3.4 `request --run-dir D [--readers-root DIR]` (the local fleet)

readers' root screened and its identity read first (section 11). Every summons gets a fresh copy (A4): the
packet builder decides the packet again from the reviewed commit and cuts it into `summons/<call id>/`, a
directory that must not exist yet (a call id is single-use), under a `summons` folder that is no link and
lies inside the run directory (C1A5-3: a `summons` link, or one resolving outside the run directory, is
refused with exit 5 before any copy is written); immediately before the request files are
written, every copy is held file by file (path, size, sha256) to the builder's own output and its
fingerprint to the one `scope` recorded. Any difference is refused (exit 5): the copies this command cut
are removed and no request file is written. One request per lens, built by
`station_core/readers_request.py`: the local row, its profile, the call's copy as the workspace, its
`documents/spec.md` and (when the commit's `REVIEW.md` is the kit sheet) `documents/REVIEW.md` as
documents, its mandate, `floor: opus`, `session_model` on `claude-session`, call id
`<run id>-local-<lens>`, `run_dir` `<run dir>/readers`; no `authorized`, `model`, `effort`, `isolation` or
`raw_path`. A Claude Code run with no `station.session_model` is refused. Writes `summons/`, `requests/`
and `requests-local.json`. `--resend LENS --status S` builds the one re-send a lens may take, call id
`<first id>-2`, only after `transport-failed`, `empty` or `incomplete` and only once (exit 5 otherwise), on
its own fresh copy: a reader's scratch, or anything planted in an earlier copy or a preview, never reaches
it.

### 3.5 `record-local --run-dir D --answer FILE`

The answer (kind `local`): the merged findings, each stamped, the method the local review used to verify,
and what each lens tried to break. Each call's status, model, profile, parity, isolation, reason and raw
file are read from readers' sidecar (a call with none is refused, and so is an `ok` call whose capture,
`readers/<call id>/raw.md`, is elsewhere or no longer matches readers' `raw_hash`). A lens whose last call
is not `ok`: a retryable failure not yet re-sent is refused with the re-send command; otherwise the run
stops (`local-incomplete`), or (`floor-refused`) on a floor refusal. The findings are held to section 6; a
refusal is exit 5 and nothing is written. `record-local` is the only writer of the local verdict: when it
completes it writes `local.json` (its calls, findings, what each lens tried, the method, and the time it was
recorded, `at`), then `local-receipt.json` (`references/local-receipt.schema.json`, closed: its version; the
run id; each local call's id, row and lens with the sha256 of the sidecar and of the capture readers wrote
for it, null where a call has no capture; the sha256 of `local.json`; the time, the same `at`), then the
checkpoint, and one trace line per summons.

### 3.6 `request --run-dir D --outside [--row ROW ...]`

Only after `record-local` completed (reading CR-5; A4): the checkpoint at `recorded-local` AND the receipt
holding, every field of it checked (C1A3-4): present and valid against its closed schema (its version), for
this run, naming exactly the local calls this run requested (id, row and lens, in request order), every
hash in it matching the file on disk now (`local.json`, each sidecar, each capture, and no capture where it
recorded none), its time the time `local.json` records, and `local.json` still holding the way
`record-local` holds an answer (the answer schema, the calls read again from the sidecars, the findings,
the credits and what each lens tried). Otherwise exit 5, and no outside file (request, copy or
`requests-outside.json`) exists under the run directory. The checkpoint's phase alone never suffices.
`verdict` holds the run to the same check (section 3.8).

**The threat model.** The run directory is the station's, and nothing in it is secret: an executor, a
reader or a person with the run directory open can edit any file there. A hand edit is not prevented; it
is detected. The receipt fixes the bytes of every file the local verdict rests on at the moment
`record-local` completes, so any later edit to `local.json`, a sidecar, a capture or any field of the
receipt itself (its version, run id, calls, hashes, or its time, which must equal the time `local.json`
records), and any checkpoint set by hand with no receipt behind it, makes the hashes, the requested calls,
the times or the re-derived record disagree, and the run refuses before any outside request exists and
before the verdict is written. Rewriting the record and its receipt together so both agree is the one edit
the hashes cannot see; it still has to pass `record-local`'s own rules against readers' sidecars, so what
reaches the outside fleet and the verdict is never less than a local review `record-local` would have
accepted.

One request per row the answer named (or the `--row` subset): `authorized: true`, decided by
`station_core/readers_request.py` from the answer's rows and nothing else; refused (exit 5) for a row the
answer did not name, a Claude row the answer named (a Claude row is never an outside reviewer and never
carries `authorized`), a row the ask did not offer (reading CR-6), a row given twice (C1A2-2), and a
`--row` subset that leaves out a named row suggest reported available (C1A2-1: one command sends every
named survivor, so none is left unsent and unnamed). A named row suggest reported dropped is never sent
(C1A-1, survivors continue): it is recorded in `requests-outside.json` under `dropped` with its status
`dropped at suggest` and suggest's reason, and the survivors are requested; when every named row was
dropped, nothing is summoned, an empty `outside.json` is written and the run moves to `recorded-outside`,
so the verdict follows on the local review. Every dropped row is named in the Method line and the
`VERTICAL:` block. Each request gets its own fresh copy, as in section 3.4. A packet-only request carries
`output_budget: 32768`; a model id the owner typed rides as `model`. Writes `summons/`, `requests/` and
`requests-outside.json`.

### 3.7 `record-outside --run-dir D --answer FILE`

The answer (kind `outside`): the verified findings and the executor's ledger notes. A call that is not `ok`
is a dropped reviewer, recorded with its status and reason; no finding may be credited to it. Writes
`outside.json` and one trace line per summons.

### 3.8 `verdict --run-dir D [--records-root DIR]`

At `recorded-outside`, or at `recorded-local` when the answer named no outside row. First the local receipt
is checked exactly as `request --outside` checks it (section 3.6; C1A3-5): when it does not hold, on a
local-only run or after the outside fleet, `verdict` refuses (exit 5) and writes nothing. The merge, the count,
the ledger comparison and the one write (reading CR-8): see `scripts/vertical_core/verdict.py`'s rules,
stated in section 6. The doc is found by glob over `docs/reviews/*-vertical-<feature>.md` (`<feature>` the
doc's topic, v1's rule): none, created as `docs/reviews/<date>-vertical-<feature>.md`; one, a dated block
appended at its end with every earlier byte untouched; several, a stop (`verdict-doc-ambiguous`) with
nothing written. A target that is a link or lies outside the workspace's `docs/reviews/` is refused
(`write-refused`). Report-only writes nothing. Every packet's workspace and documents, the previews and
the summons copies, are removed afterwards; the mandates and the lists stay. A run that stops anywhere
removes them the same way when it writes its result (C1A3-6), so no copy of the reviewed tree outlives a
run.
Writes `verdict.json` and the doc.

### 3.9 `report --run-dir D --bottom-line TEXT [--skill-note TEXT]`

The completion: `result.json` and the `VERTICAL:` block (`chat.md`), exit 10.

### 3.10 `identity <workspace>` and `skill-identity`

The E14 driver's, unchanged: the workspace as this station sees it; the skill's name, version, commit and
content hash.

## 4. The input

`references/input.schema.json`, closed at every level. The shared fields are `references/back-loop.md`
section 3's. `station`: `depth` (`LEAN` or `DEEP`, the executor's statement before launch), `session_model`
(the model id the session reports for itself), `date` (the verdict doc's date; absent, today's UTC date),
and `owner_words`, the owner's own words in this run, verbatim and the one source of each: `collapse_gate`
(the gate's collapse), `committed_only` (a committed-state-only order over dirt in the boundary), `base`
(`commit` and `words`, his answer to the base question). The ask's answer arrives through `ask --answer`.

## 5. The base, the scope and the copies

**The base** (reading CR-2), v1's precedence: (1) a base the build doc records: the header's one exact
`Base:` line (section 5, "Exact labels", A10: `Base: ` and 7 to 40 lowercase hex characters, nothing after but
spaces or tabs, the last line of its paragraph, at most one before the first `## ` heading), read outside
fences under the fence rule (A7, A8: a fenced `Base:` or `## ` line is content; A9: a `Base:` inside an HTML
comment makes the doc unreadable; A10: a `Base:` held hidden in a link title, a link reference definition or
an inline comment, a second `Base:` line, or one with any other value or text after it makes the doc
unreadable, it is never the base); (2) `git merge-base <default branch> HEAD`, the default branch being the remote's
`HEAD` when one is named, else `main`, else `master`, and a merge base equal to HEAD itself counting as
none (nothing to review); (3) the owner's base from `station.owner_words.base`; else a stop that asks
(`base-unresolved`). A `Base:` header line whose value is not 7 to 40 lowercase hex characters (a branch
name, `HEAD`, upper-case hex, too short) stops the gate `doc-unreadable` under the label rule (A10), and the
owner's base never clears it (A11, "no override"): the plan's author edits the doc. An exact `Base:` line that resolves to no commit, or that
names HEAD itself (an empty boundary), cannot be taken (C1A-7): the owner's base in the input, on a fresh run,
is taken over it, and the Method line names both (C1A2-3); with none, the run stops (`base-unresolved`)
naming the line and where his answer goes. An owner's base that names HEAD itself is never taken, wherever it would be, and stops
(`base-unresolved`) saying the boundary would be empty (C1A2-4). The base and how it was found go in the
Method line.

**The boundary** is `git diff --name-status <base>..HEAD` (a rename keeps its old path too). The clean-tree
rule reads `git status --porcelain` against the boundary's paths and the build doc; a rename or copy in the
tree names both its paths, so a boundary file moved away is dirt on the boundary (C1A-8).

**The packets, from the reviewed commit only** (reading CR-3; A2, Q1; A4). Every reviewer workspace and
every packet, local and outside, preview, first send and retry, is built by one function
(`scripts/vertical_core/packet.py`) from the objects of the commit `gate.json` records: its tree through
`git ls-tree -r` and its stored bytes through `git cat-file --batch`, never the working tree and never an
earlier copy. `git archive` is not used because it applies the reviewed repo's committed `.gitattributes`
export rules and cannot be told not to (`export-subst` writes commit messages into files, `export-ignore`
drops tracked files without a word, C1A-5), so every file holds the bytes the commit stores, with no
attribute, filter or line-ending rule applied. No packet or workspace carries `.git`, history or a commit
message. A copy is cut into a directory that does not exist yet, and every summons gets its own.

**The allow rule**, the one rule for what enters (the code's statement is `packet.left_out_by_rule`). A
path reaches a reviewer's workspace when, and only when, it is a blob of the reviewed commit's tree (a
file, an executable, or a symbolic link written as a plain file holding its target text) and none of these
holds: (1) it is not a plain relative path; (2) two consecutive components of it read `docs` then
`reviews` (a prior verdict) or `docs` then `records` (the records log), without regard to case, wherever
they stand; (3) any one of its components, a folder's name as well as the file's, lower-cased with `-`,
`_`, `.` and spaces removed, holds `buildernotes` or `buildnotes` (the builder's notes, B4), or it is a `.md`
regular file whose first heading declares it the builder's notes (C1A3-3, the slice review's rule, restated
below); (4) it is `REVIEW.md` at the root. The build doc's file in a workspace holds the spec. A submodule is not a file
and is not copied. What each packet holds: a local lens, the workspace, `documents/spec.md`, the commit's
`REVIEW.md` as `documents/REVIEW.md` when it is a regular file and the kit sheet, and its mandate; an
outside row on `repo`, the workspace and the outside mandate; an outside row on `packet-only`, the
workspace's UTF-8 files staged under `documents/` with every `/` written `__` (two paths that stage to one
name: the first in path order keeps it and each later one takes it with `.2`, `.3` and on before its
extension, never a name another path stages to, C1A-6) and the outside mandate. The inspection sheet is
read from the commit's `REVIEW.md` alone (B1): an untracked or changed working-tree `REVIEW.md` never picks
a lens, never reaches a mandate, and never reaches a packet.

**A notes file declared by its first heading** (C1A3-3; `scripts/vertical_core/notes.py`). The slice review
withholds a Markdown file whose first heading says it is the builder's notes; so does this core, reading the
commit's bytes of every `.md` regular file but the build doc. A heading declares when it holds "notes from
the builder", "builder notes", "builder's notes", "builders notes" or "build notes", letter case aside (and,
since A16 and its send-back 1, read folded, "The fold" below, with a curly apostrophe, U+2018 or U+2019, read as
`'`, the same in both readings, `notes.declares_name`).
Which heading is first is read wide, so a declaration a Markdown reader would see first is never missed:
every heading-shaped line (an ATX heading, or the text above an `===` or `---` underline), with block-quote
and list markers stripped, whatever holds it (a fence, raw HTML, a container, front matter), counts until
the first certain heading, an ATX heading at the left margin outside every fence the fence rule accepts and
before the first fence line it does not accept or raw HTML line (past such a line no heading is certain,
C1A4-1, A9), with no line opening with `<` before it and past any front matter; that heading counts too, and nothing after it.
Reading wide only ever withholds more, and what it withholds is named with the heading that declared it. A
notes file is not the build doc: a fence line the rule does not accept, or a raw HTML line, there never stops
the run. Since A13 each such file is also read by the CommonMark reader ("Two readings" below). Since A14 (C1A8-4)
only one direction stops the run, named with its line: the CommonMark reader's first heading declares the file the
builder's notes and the line reading does not (the file would reach the packets). A file the wide line reading
declares and the CommonMark reader does not (an ordinary file that opens with an HTML line and has a later
`## Build notes` heading) is withheld and named, as before A13; it never stops the run. The declaration test reads
the heading folded ("The fold" below, A16 (3), A17 (1)). Since A16 (2), before either reading is asked, a
file one of whose heading lines holds a character outside the character list ("The character list" below) is a notes
candidate: withheld and named with the line and the character, never a stop (the code's statement is
`scripts/vertical_core/notes.py`, "A HEADING LINE OUTSIDE THE CHARACTER LIST", with `readings.notes_unlisted`). The
heading lines tested are the ones the declaration test itself reads (send-back 1 of fix round 10): the line reading's
candidates up to and including the first certain heading (an ATX heading's line, or a Setext heading's text lines and
its underline line, A17 (3)), never a line an accepted fence holds, found three times (A17 (3), C1A10-3): in the file
as written, with the characters outside the list removed on each line, and with the characters outside the list read
as spaces (so `#`, a no-break space, then `Builder notes`, and `Builder notes` over `===` and a Hangul filler, are
found), each line found tested as written; and the
CommonMark reader's first heading, rendered and before its whitespace is collapsed, so a character reference counts as
the character it names. A heading past the first certain heading, or a fenced sample, holding such a character leaves
the file an ordinary one.

**The fence rule: strict plain code blocks** (A8, C1A4-1; the code's statement is
`scripts/vertical_core/fences.py`; the frame's `templates.py` stays frozen and is not used for it). A fence
line is any line whose first characters, after any indent (spaces or tabs) and after any block-quote markers
(`>`) or list-item markers (`-`, `+`, `*`, or one to nine digits then `.` or `)`, followed by a space or a
tab), are three or more backticks or three or more tildes. A fence is accepted only when its opening line
starts at column 0 (no indent, no list marker, no `>`) with three or more backticks or tildes (a backtick
opening line's info string holding no backtick, CommonMark's rule); its closing line is the first later line
that starts at column 0 with the same character, at least as many times, and nothing after it but spaces or
tabs; and no line between them is a fence line off column 0. Every other line between is the fence's content,
whatever it looks like. ANY other fence line anywhere in the build doc (one off column 0, a backtick line
whose info string holds a backtick, an opening line never closed) stops the run `doc-unreadable` with its
line number, before any ask, request or packet: the plan's author edits the doc. The reader follows no list,
block-quote or lazy-continuation rule. Every reader of the build doc goes through this one rule and the next
three, and then through the second reading ("Two readings" below): the gate's slices and `Status:` lines, the
`Base:` line, the spec and its sections.

**No raw HTML lines** (A9, C1A5-1 and C1A5-2; the code's statement is `scripts/vertical_core/fences.py`). A
raw HTML line is any line outside an accepted fence whose first characters, after any indent (spaces or tabs)
and any list-item or block-quote markers (the same prefix as a fence line's above), are `<` followed by an
ASCII letter, `/`, `!` or `?`. Every such line stops the run `doc-unreadable` with its line number, before any
ask, request or packet, and the plan's author edits the doc: a tag, a closing tag, a comment, a processing
instruction, a declaration or a CDATA section, and also a line that only opens with an inline `<placeholder>`
or an autolink (by design: the rule never asks which a line is). The reader does not track where a raw HTML
block ends, so no heading, `Status:` label or `Base:` line inside raw HTML is ever read as structure, and no
Unicode space line can end a block early for the reader. A `<` line inside an accepted fence is content; a
`<` later in a line, or followed by anything else (a space, a digit, another sign), is text.

**Exact labels** (A10 and A11, C1A6-1; the code's statement is `scripts/vertical_core/fences.py`, "THE LABEL RULE", read
through `fences.read` by every reader of the build doc). Outside accepted fences, a `## ` line matching the
build-doc form's slice heading opens a slice's section and any other `## ` line closes it; the header is every
line before the first `## ` line. A line "starts with `Status:`" (or `Base:`) when it is a label candidate (A16
(3)): folded ("The fold" below) it opens with `status` (or `base`), any spaces or tabs, then a colon, so `status:
built`, `STATUS: built`, `Status : built` and `St` U+00E4 `tus: built` are such lines and, not being exact, stop (and so
is `B` U+00E4 `se: 1234567` in the header). Inside a slice's
section, a line that starts with `Status:` is the slice's label only when (a) it reads exactly `Status: ` (one space)
and one of the six values A11 rules, `not started`,
`in progress`, `built`, `rejected`, `signed off with conditions`, `signed off` (a `rejected` or conditional slice
stops `gate-short` and the owner's collapse words apply, as before A10), with nothing after but spaces or tabs,
and (b) it is the last line of its paragraph: the next line
is empty or holds only spaces and tabs (never any other Unicode space), is an ATX heading, opens an accepted
fence, or the doc ends. A slice holds at most one. In the header, a line that starts with `Base:` is the
recorded base only when it reads exactly `Base: ` and 7 to 40 lowercase hex digits, with nothing after but
spaces or tabs, and meets (b); the header holds at most one. Any other line starting with those labels there (a
wrong value, upper case, text after it, a no-break space, a following paragraph line or a Setext underline, a
second label) stops the run `doc-unreadable` naming the line (both lines for a second label), before any ask,
request or packet, and the plan's author edits the doc. Why it holds: CommonMark renders nothing of a line held
inside an inline comment opened mid-line, a link reference definition's title or an inline link's title, and
each needs a closing mark after the held line in the same paragraph; the exact value leaves no room for one on
the label line and the paragraph's end leaves no later line. A slice whose only label is hidden stops the same
way; a slice with no `Status:` line at all stops `gate-malformed`. A `Status:` line outside every slice and a
`Base:` line outside the header are no label (the spec still removes every `Status:` line, below).

**Plain structure** (A12, C1A7-1; the code's statement is `scripts/vertical_core/fences.py`, "THE PLAIN-STRUCTURE
RULE", read through `fences.read` by every reader of the build doc). Outside accepted fences, a line that, after
any indent and any list-item or block-quote markers (the fence rule's prefix), opens like an ATX heading (one to
six `#`, then a space, a tab or the line's end) or like a `Status:` or `Base:` label (a label candidate, folded, as
"Exact labels" reads it, A16 (3)) is read only when it is plain: at column 0 with no marker, a heading being one to
six `#` then exactly one space, a label then read as
"Exact labels" rules. Every other such line stops the run `doc-unreadable` with its line number, anywhere in the
doc (inside a slice, in the header, between sections), before any ask, request or packet, and the plan's author
edits the doc: a heading or a label indented by spaces or a tab, after a list-item marker or one or more `>`;
`##` then a tab, a bare `##`, `##` then two spaces. CommonMark renders a heading indented one to three spaces,
with a tab after its `#`s or with nothing after them, and a label indented one to three spaces, just as their
plain forms, so a slice heading the reader never took could carry a rendered `Status: built`, or a real slice
could show an indented `Status: built` while its one exact label sat in a lazy quote or list line or under an
empty `##`; the reader takes structure only in the plain form and refuses the rest. A problem line is never read
as structure. A `#` with no space after it (`#hashtag`), seven or more `#`, and a `Status:` or `Base:` later in
a line are text; a line inside an accepted fence is content.

**The character list** (A16, C1A9-1; the code's statement is `scripts/vertical_core/fences.py`, "THE CHARACTER
LIST", the constant `LISTED`). Outside accepted fences, every character of the build doc must be printable ASCII
(U+0020 to U+007E), a tab, a line ending (LF, CR, CRLF) or a byte order mark at the start of line 1, or one of the
fixed list: the punctuation and symbols the owner's real plans use (U+00A7, U+00B2, U+00B7, U+00D7, U+2013, U+2014,
U+2019, U+2026, U+2190, U+2191, U+2192, U+2193, U+2194, U+2197, U+2212, U+2248, U+2264, U+2265, U+2715), the curly
quotes U+2018, U+201C, U+201D, and the accented Latin letters U+00C0 to U+00FF except U+00F7. Any other character
stops the run `doc-unreadable`, naming the character (its code point, its Unicode name, its column) and its line,
before any ask, request or packet, and the plan's author edits the doc: a format character, a Unicode space, a
default-ignorable or combining mark, a Hangul filler, a braille blank, a control character, a letter of another
script, a full-width form, an emoji. The rule comes after the fence rule (a character inside an accepted fence,
its opening and closing lines included, is never refused); on one line a fence line's or a raw HTML line's problem
is named first, then the character, then a plain-structure or label problem (a label that only looks exact is named
for the character that makes it so). Why it holds: each round of the class found one more character a reader renders
as nothing, or as a letter it is not, in front of a label, a base, a slice heading, a withheld heading or a label
heading, so both readings missed the structure a person sees; a short list of the characters the plans really use
leaves none to find. A character reference that the CommonMark reader decodes to a character outside the list stops
the run too (refusal (d) below). On the 25 real plans one line in one plan holds a character outside the list (a
right-to-left override), and that plan stops until its author edits the line.

**Two readings** (A13; the code's statement is `scripts/vertical_core/readings.py`, "THE TWO-READINGS RULE", read
through `spec.read` by every reader of the build doc and through `packet.declared_notes` for every other Markdown
file). The build doc is read twice: by the line rules above (the fence rule, no raw HTML lines, exact labels and
plain structure, kept as they are and applied first, so a doc they refuse is refused naming their line), and by a
pinned CommonMark reader (`scripts/vertical_core/commonmark.py`, the one module that imports it: `markdown-it-py`
3.0.0 with `mdurl` 0.1.2, vendored, the `commonmark` preset; section 15, "Runtime"). The CommonMark reading takes
its headings from the token stream (the level, the rendered name, the first line from the token's map) and its
labels from the rendered paragraph lines (split at soft and hard line breaks); a rendered name or line is the inline
text with character references and backslash escapes decoded, inline markup removed (emphasis, links, images and
code spans keep their text; inline HTML is dropped) and whitespace runs collapsed, Unicode spaces included. Then the
decisions are compared, never the text: (1) the slices, each one's name and heading line (a level 2 heading, ATX or
Setext, wherever it stands, whose rendered name matches the build-doc form's slice pattern); (2) each slice's card
(the rendered paragraph lines starting with `Status:` from its heading to the next heading of level 1 or 2, every
one kept, a list, never one entry per source line, A14, C1A8-1: none is no card, one exact label is its value,
anything else is a card the line rules never take); (3) the recorded base (the rendered paragraph lines starting
with `Base:` before the first slice heading, kept and decided the same way); (4) the withheld sections, each
withheld line's section and the name its heading was read from, both readings applying the withheld-name rule
("The spec" below, A14) to their own reading of the name, and each section's first and last line; and (5) for every
other Markdown file of the reviewed commit, its builder's-notes declaration, where only the leaking direction
stops (A14, C1A8-4: the reader's first heading declares the file and the line reading's wide first heading does
not; a file only the wide reading declares is withheld; a file with a heading line holding a character outside the
list is withheld before either is asked, A16 (2)). Any difference stops the run `doc-unreadable`, naming the
first line where the two readings take a decision differently and which decision, before any ask, request or
packet, at every reader: the gate's slices and base and its notes check of HEAD, the spec, the packet snapshot.

**Hidden labels** (A15; the code's statement is `scripts/vertical_core/fences.py`, "THE HIDDEN-LABEL RULE",
`label_form`). A line reads as a `Status:` or `Base:` label when, after every format character (Unicode category Cf:
a zero-width space, a soft hyphen, a zero-width no-break space, a word joiner) is removed and its leading whitespace
(any Unicode space: a no-break space, an ideographic space) is stripped, it starts with that label, "starts with"
read as a label candidate (A16 (3): folded, "The fold" below, then `status` or `base`, any spaces or tabs, a
colon). Since A16 such characters stop the run under the character list before this test is reached; it stays as
the second reading's own guard for a rendered line. The CommonMark
reading tests every rendered paragraph line this way for the cards (2), the base (3) and refusal (a) below, so a label
hidden behind such characters is a label candidate: a second or a non-exact label the line rules never take, and the
run stops `doc-unreadable` naming its line, before any ask, request or packet. The spec removes every line outside
fences that reads as a `Status:` label this way ("The spec" below), so a hidden one no card reads (in the header,
between sections) reaches no packet and is named in every withheld list.

**The CommonMark reading's four refusals** (A14 and A16; the code's statement is `scripts/vertical_core/readings.py`,
"THE SECOND READING'S FOUR REFUSALS"). A doc the line rules accept also stops `doc-unreadable`, naming the line, before
any ask, request or packet, when the CommonMark reading finds: (a) a rendered paragraph line that starts with
`Status:` or `Base:` in a paragraph whose rendered lines cannot all be mapped to source lines (a code span, a link
destination or a link title running over a line ending), anywhere in the doc and whatever the label says, one
exact label included, named at the paragraph's first line (C1A8-1: which source line holds which label cannot be
told there, and two rendered labels once collapsed into one); (b) a heading of level 1 or 2 whose rendered name,
with format characters (Unicode category Cf) removed, folded ("The fold" below, A16 (3), A17 (1)) and its leading
punctuation, symbols and spaces (Unicode categories P, S and Z) set aside (A17 (1), C1A10-1), starts with `slice` and
is not a level 2 heading whose rendered name matches the build-doc form's slice pattern (C1A8-2: an en dash, a hyphen
or a colon for the form's dash, no spaces around it, a lower-case `slice`, a zero-width character, a level 1 heading;
C1A10-1: an accented letter such as `Sl` U+00EF `ce`, a leading curly quote such as U+2018 before `Slice`; no reading
would take it as a slice, so its slice would vanish from the sign-off check, where v1's gate read every slice
heading's label); a heading of level 3 or more, such as a `### Slice D` note with a date, is not touched; (c) a
heading of any level whose rendered name, with format characters removed, is a label candidate (A16 (3):
`### status: built`, `### Status : built`) (C1A8-3: no reading takes a heading as a label, so its words would stand
beside the slice's card or the base, unread); (d) a rendered heading name or paragraph line, before its whitespace is
collapsed, holding a character outside the character list (A16 (1), named with its code point): once the line rules
have accepted every source character, only a character reference (`&#x3164;`, `&nbsp;`) can put one there, and the
reader renders it as the character it names. Each refusal reads the rendered heading or line, which for a plain line
is its source text, so one rule covers the source form and every rendering of it. The plan's author edits the doc (the
form's slice heading, a plain slice heading, a plain label in a paragraph of its own, an ATX heading for a withheld
section, no character reference where a decision is read). A doc both readings take the same way runs exactly as
the line rules alone run it; a heading whose markup leaves every decision equal (a code span or bold in a slice's
short title) still runs. Why it holds: each family the line rules missed (a Setext heading, a character reference,
inline markup in a heading, extra spaces in a slice heading, an escaped, bold or character-coded `Base:` line) is a
place where what a Markdown reader renders differs from the source line; the second reading renders it, so the
difference is seen instead of modelled. A heading both readings take as no slice, a near-miss withheld heading
and a heading named like a label were outside the comparison; since A14 the refusals above and the
withheld-name rule cover them.

**The fold** (A16 (3), A17 (1), C1A10-1; the code's statement is `scripts/vertical_core/fences.py`, "THE FOLD",
`fold`). Every label test (the label rule, the plain-structure rule, the spec's removal, the CommonMark reading's
cards, base and refusals (a) and (c)), every slice-heading test (refusal (b)), every withheld-name test (the spec's
withheld-name rule, below) and the builder's-notes declaration test compare the text folded: NFKD normalization with
every combining mark (Unicode category M) removed, then NFKC normalization, then case folding. So an accented letter
the character list admits folds to its plain letter (`St` U+00E4 `tus` reads `status`, `Sl` U+00EF `ce` reads `slice`,
`B` U+00E4 `se` reads `base`, `P` U+00FC `nch` reads `punch`), a compatibility form folds to its plain form, and upper
case to lower case; a letter the list admits hides no label, slice heading or withheld name from both readings. On the
25 real plans the fold changes no decision.

**The spec** (reading CR-4; ruling E15-8 as A3 widened it and A4 and A5 amended it) is the commit's build doc
with five sections and every `Status:` label removed outside fences, what is fenced decided by the fence rule
above (A5 (2), A8); a build doc holding a fence line the rule does not accept, a raw HTML line (A9), a label
line the label rule does not take (A10), or a heading or label line off the plain form (A12), stops the run at
`scope` (`doc-unreadable`, naming the line) before any packet is built. The sections removed: `## Punch list` and `## Handoffs` (the ledger) and `## Build
assumptions`, `## Deviations` and `## Discovered` (the builder's working records, which the slice review
withholds too), each found by heading level and name under **the withheld-name rule** (A14, C1A8-3; the code's
statement is `scripts/vertical_core/spec.py`, "THE WITHHELD-NAME RULE", `withheld_of`): a heading of level 1 or 2
(on the plain form, A12; a heading off the plain form has already stopped the run) whose name, with any closing
hashes dropped, its format characters (Unicode category Cf) removed, folded ("The fold" above, A16 (4), A17 (1)), its
hyphens, dashes (U+2010 to U+2015), underscores, minus signs (U+2212), middle dots (U+00B7) and curly single quotes
(U+2018, U+2019) read as spaces (A17 (2)), its whitespace runs collapsed (C1A2-5), and every leading numbering (digits
with dots or a closing parenthesis, `1`, `1.`, `1.1`, `2)`; a parenthesized number, `(1)`; a single letter with a dot,
`A.`; A17 (2)) or leading `the` dropped, STARTS WITH one of the stems `punch`, `handoff`, `hand off`, `build
assumption`, `buildassumption`, `builder assumption`, `builderassumption` (A17 (2)), `deviation` or `discover` is the
withheld section the stem names (`## Punch list`, `## Handoffs`, `## Handoffs`, `## Build assumptions` for the four
assumption stems, `## Deviations`, `## Discovered`), and is named as that section in every withheld list. So a near
miss (`## Punch-list`, `## Punch list:`, `## Handoff`, `## Hand-offs`, `## Hand off`, `## Hand` en dash `offs`,
`## Hand` U+2212 `offs`, `## Hand` U+00B7 `offs`, `## Hand` U+2019 `offs`, `## H` U+00E0 `ndoffs`, `## P` U+00FC
`nch list`, `## 1 Punch list`, `## 1. Punch list`, `## 1.1 Punch list`, `## (1) Punch list`, `## A. Punch list`,
`## The punch list`, `## Build-assumptions`, `## Buildassumptions`, `## Builder assumptions`, a dated
`## Handoff, <date>`) is withheld, never sent; a wider match only ever withholds more (since A17 a bare leading
number is numbering, so `## 10 punches` is withheld as the punch list). The name must START with a stem once its
numbering and `the` are dropped: the rule does not withhold a name that only contains one (A17 rejected a contains
rule, which would withhold an ordinary heading of a real plan), so `## Open punch list` reaches the packets (a carried
item), and `## Theory`, `## Handy offsets` and `## A note on punctuation` are ordinary sections. The CommonMark
reading applies the same rule to the rendered name, and the two readings must agree on every withheld line, its
section and the name it was read from ("Two readings" above). Each section runs to the line
before the next heading of level 1 or 2 outside a fence; and every `Status:` label (a line outside fences
that starts with `Status:`, the build-doc form's label test), in a slice's section or out of one, the
header's included (M6), each read after its format characters are removed and its leading whitespace stripped
("Hidden labels" above, A15) and as a label candidate (A16 (3), so `status: draft` and `Status : draft` go too).
Everything else stays byte for byte.

**The withheld list** of every packet names everything left out, each with why, and nothing the packet
holds: every tracked path the allow rule left out (each prior verdict, each records log file, each
builder's notes file, a folder's files one by one, each file its first heading declares), each submodule,
each removed section and `Status:`
label with its line numbers, every untracked and ignored path and every changed working-tree path (the
names `scope` read once, never their contents), the commit's `REVIEW.md` where the packet does not receive
it (every outside packet; a local packet when it is not the kit sheet or not a regular file), and on a
packet-only row each file that is not UTF-8 text.

vertical-v2 never runs `git worktree`, never runs a git command that changes a branch, an index or a
worktree, and removes every packet's workspace and documents after the verdict or a stop (C1A3-6). The
removal never follows a link (C1A4-3): a link at `packets` or `summons`, at an entry in either, or at an
entry's `workspace` or `documents` is removed as a link, never its target, and a folder is removed only when
its real path lies inside the run directory's; nothing outside the run directory is deleted.

## 6. The review mechanics

Restated in this core's own words from the slice review's contract (ruling E15-6); nothing is read from
another skill at run time.

**Independence.** Fresh reviewers originate the findings, never the session that runs this skill. Each
receives its packet and its mandate and nothing from any session: no chat, no reasoning, no other
reviewer's output, no prior verdict. The local fleet's findings are recorded before any outside request
exists.

**The finding shape.** A claim (one line), a location `file:line` (or `file:line-line`) in the reviewed
copy, a concrete failure scenario, a severity (BLOCKER, MAJOR, MINOR) and a confidence (high, medium,
low), credited to the readers call ids whose reports hold it. A concern with no location never reaches the
verdict unless the executor verifies it into a real `file:line`.

**The evidence rule and verify before reporting.** The executor reads the source at every finding's
location, checks the scenario, and stamps it: CONFIRMED, PLAUSIBLE, or REFUTED with its reason. The script
refuses (exit 5) a CONFIRMED or PLAUSIBLE finding whose file does not exist in the reviewed copy or whose
line lies past its end (a packet-only `__` name is read back to its path first), a REFUTED one with no
reason, a severity or confidence changed from the reviewer's stated one with no reason, a finding credited
to a call that is not this phase's or did not come back `ok`, and a field holding the line form's
separator or a line break.

**The anti-rubber-stamp rule.** A lens credited with no finding says what it tried to break and could
not, each entry with how (`executed`, `read`, `reasoned`) and, when executed, its output; an empty account
is refused. A local review whose lenses executed nothing says so in the Method line.

**The severity to verdict mapping**, over the verified findings, arithmetic: any BLOCKER is `REJECTED`;
else any MAJOR is `SIGNED OFF WITH CONDITIONS`; else `SIGNED OFF`. BLOCKER: a spec requirement unmet, or a
defect that loses data, corrupts state or breaks a shipped feature. MAJOR: a real defect with a concrete
failure path, contained and fixable in place. MINOR: a rough edge, a missing guard, a thin test.

**Dedupe and convergence.** Findings are merged on `file:line` and claim; one merged finding names every
reviewer that found it (local lenses as `local:<lens>`, outside rows by row), at the gravest severity
among its verified members. `Refuted: N` counts the merged findings no member of which survived.

**The repeats and misses.** Against the ledger read through the records component's `state`: a verified
finding at a ledger finding's file and line, or with its claim in the same file, is a repeat with the
ledger's disposition; a ledger finding marked fixed that no verified finding re-found is a miss for the
executor to verify. The executor's prose on them rides as the ledger notes.

**The inspection sheet, `REVIEW.md`.** It is the sheet only when it carries the three headings `## Passes`,
`## Severity bar` and `## Repo-specific checks`, and every non-blank line under `## Passes` reads
`- <name>: on` or `- <name>: off` with an optional parenthetical; otherwise it is `present but not the kit
sheet` and the defaults apply; with no file, `absent`. The passes it may name are `correctness`,
`security`, `accessibility` and `data-safety` (another is reported unknown and ignored). A pass `off` is
never run, even at DEEP, and the verdict names the skip with its reason; a pass `on` adds its lens; `spec`
and `seams` are never off. Its severity bar is the repo's meaning column for defects (a spec requirement
unmet stays a BLOCKER, and the three verdicts do not change), and each repo-specific check is an item the
local lenses try to break. It reaches the local lenses only: its checks are distilled from prior verdicts.

**The lenses.** LEAN: `spec`, `correctness`, `seams`; DEEP adds `security` and `tests`; then the sheet's
passes. The briefs are `references/lens-briefs.md`.

## 7. Stops and exits

The exit codes are `references/back-loop.md` section 2's. Every stop writes `result.json` and exits 10.

| Tag | When |
|---|---|
| `selection-none` | the hunt found no build doc; ask the owner and run again with `--doc` |
| `selection-several` | the hunt found several; listed for the owner, none picked |
| `gate-malformed` | zero slices, or a slice with no `Status:` line |
| `gate-short` | a slice stands short of `signed off` and the owner's words did not collapse the gate |
| `card-disagrees` | a slice's observed card in the records disagrees with its `Status:` line (a derived card that differs never stops; it is named in the Method line) |
| `records-refused` | the records component refused a read; its own sentence is carried |
| `not-git` | the workspace is not a git work tree root with a commit |
| `base-unresolved` | no base: none recorded, no merge base, none from the owner; an exact recorded `Base:` line that resolves to nothing or names HEAD itself, with no owner's base to take over it; or an owner's base that resolves to nothing or names HEAD itself |
| `dirty-boundary` | dirt touches the boundary or the build doc and the owner gave no committed-state-only order |
| `doc-unreadable` | at `gate`, before the ask (the working tree's build doc), or at `scope`, before any packet (the reviewed commit's build doc): it holds a fence line the fence rule (section 5) does not accept (off column 0, in a list item or block quote, a backtick info string holding a backtick, never closed), a raw HTML line (section 5, "No raw HTML lines"), a slice `Status:` line or header `Base:` line the label rule does not take (section 5, "Exact labels": not exact, not the last line of its paragraph, or a second one), or a heading or label line off the plain form (section 5, "Plain structure": indented, after a list-item or block-quote marker, or a heading whose `#`s are not followed by exactly one space), or a decision the line rules and a CommonMark reader take differently (section 5, "Two readings": the slices, a card, the recorded base, the withheld sections), or a character outside the character list outside an accepted fence (section 5, "The character list", A16: named by its code point), or one of the CommonMark reading's four refusals (section 5, "Two readings", A14: a rendered `Status:` or `Base:` line in a paragraph whose lines cannot all be mapped to source lines, named at the paragraph's first line; a level 1 or 2 heading off the slice form that starts with "slice"; a heading that starts like a `Status:` or `Base:` label; A16: a rendered character outside the list, which only a character reference can put there); or, at `gate` once the workspace is a git work tree and at `scope`, another Markdown file of the commit that a CommonMark reader declares the builder's notes and the line reading does not; the line is named (the file too, for a notes file), both lines for a second label |
| `station-refused` | a readers root that is not the expected readers plugin by identity, or a file of it that resolves outside it, or one named for a v1 plugin folder (each refused before any of its files is opened or run), or readers' identity breaks the trace's refusal rule; a `refused` trace line is written |
| `floor-refused` | a local lens came back below the floor; no verdict is emitted |
| `local-incomplete` | a local lens failed after its re-send, or refused deterministically |
| `verdict-doc-ambiguous` | several verdict docs exist for the build |
| `write-refused` | the verdict doc's place is not a plain file under the workspace's `docs/reviews/`, or the append would change an earlier block |

## 8. The load-bearing forms

Rendered and parsed by `scripts/vertical_core/forms.py`, with a round-trip test (ruling E15-11). The
verdict doc: a title line naming the feature, then one block per run, each opening with its date and run
id and holding v1's three sections in v1's order: `### THE VERDICT` (the verdict word, `Refuted: N`, the
verified findings in the punch-list line form, severity, `file:line`, claim, scenario, reviewers, stamp,
and any re-grade; the repeats, the misses, the ledger notes, the `REVIEW.md` line and the sheet's skips and
checks), `### Method line` (the base and how, the head and boundary, the run id, the gate and any collapse,
each slice whose derived card differs from its observed card with both cards, the tree, the depth and
lenses, each local lens's row, model and profile, the route, each outside reviewer's row, model, profile,
parity, isolation, anomaly and files left out, each dropped reviewer with its status and reason (a named
row suggest dropped reads `dropped at suggest`), how the local review verified, and what every packet
withheld), and `### Unverified
appendix` under v1's banner, each reviewer's raw text verbatim between two marker lines, the opening one
carrying the text's length. The `VERTICAL:` block is v1's lines byte for byte.

**The exception to the no-dash rule.** v1's appendix banner, the `VERTICAL:` block's `Dropped:` and
`REVIEW.md:` lines and its bottom-line placeholder, the build doc's own form, and `assets/vertical-mandate.md`
(v1's outside mandate, carried byte for byte) keep v1's em dashes. Nothing else this core writes holds one.

## 9. The result

`references/result.schema.json`, validated with S1 to S4 (`scripts/validate-result.py`) before it is
written; a result that fails is a defect (exit 1), never a softened result. `station_result` carries the
gate's record, the ask's rows and words, the depth and lenses, every call with its status, model and
profile, the verdict, the finding and refuted counts, the verdict doc's path, the sheet's state, the
Method lines and, at completion, the `VERTICAL:` block.

## 10. The records component

`gate` and `verdict` read `state` through the resolver snippet and the CLI only
(`scripts/station_core/records_client.py`, `scripts/station_core/records_link.py`), after confirming
interface version 2 through `component-identity`; a missing component or another version is exit 3.
vertical-v2 writes no event and never opens the component for writing (owner pick P12, ruling E15-9).

## 11. The trace

`trace.jsonl` in the run directory, `references/trace.schema.json`, written by `scripts/back_core/trace.py`
(reading CR-9). **The readers root, by allowlist identity** (A5 (1); B5, C1A3-2;
`scripts/vertical_core/readers_link.py`). The allowlist is the expected readers plugin and nothing else:
the checkout sibling `<plugin root>/../readers` (route 3a) and each installed `<plugin root>/../../readers/<version>`
folder (route 3b, a canonical dotted version), found the records way from this core's own real plugin root,
each taken only when its parent's listing holds it under that exact name as a real directory, never a
symbolic link (so a link, or a name differing only in letter case, is never on it), and identified by the
disk's own identity, its device and inode. Before anything of a readers root is opened, every candidate is
held to it: `--readers-root` must have the identity of an allowlisted folder (so a link to the real readers
is accepted: the folder it reaches is the expected plugin, and every file is then held to that folder); route
3a's path, when anything is there, must be the allowlisted sibling; route 3b's folder must be a real
`readers` directory and each canonical version entry in it allowlisted (an entry that is not a canonical
version is never a candidate and never opened). Then every file this core opens or runs from the root it
takes (the manifest, the roster, `readers.py`) must resolve by its real path inside that root, by identity
(each parent of its real path is stat'ed until one is the root). The name-based v1 screen stays as a second
line: a root or file whose real path or own path, letter case aside, sits under a v1 plugin folder, or
holds a v1 station's name followed by a dotted version anywhere (an installed v1 version folder, however
deep), is refused too. Every refusal comes before the refused root's manifest, roster or executable is
opened or run: a `refused` line with no identity is written, with the rule `v1-root` when the name screen
names a v1 station for it and `no-identity` otherwise (nothing of it was read; the trace's rules are a frozen
back-frame file, so no rule is added), and the run stops `station-refused`. `ask` and `request` both hold
every root to it. Then readers' identity is read from the root taken (`--readers-root` when allowlisted and
usable, then route 3a, then the highest installed version whose manifest version is its folder name): the
name and version its manifest carries, its real path, and the protocol version its own CLI prints
(`readers.py --version`, which summons no reader, run isolated with `-I` and `-B`: neither its own folder nor
the user site is on `sys.path` and no `PYTHON*` variable is read, so a module planted beside it never runs,
C1A4-2). An identity the refusal rule
refuses (a name other than `readers`, a root under a v1 plugin folder, a protocol this core does not know)
stops the run (`station-refused`) with a `refused` line and no request. Every summons, whatever its status,
is a `summons` line with that identity, the route, the readers run directory, its status, call id and row.

## 12. The harness seams

Ruling E15-12 and reading CR-10. On Claude Code the local lenses are `claude-session` calls with
`repo-with-tools`, fresh subagents that may run the project's tests in their own copy. On Codex they go
through `claude-opus-cli`, the portable Claude row a shell can dispatch, with the profile that row offers:
`repo-with-tools` once readers offers it on that row (the slice 1a brief's item 4(c)), `repo` until then.
On `repo` each lens reads the code and runs no check; the ask says so, the request's route says so, each
local mandate says so and promises no test run (C1A-9), and the Method line names the route and states
"static analysis only". The row offers `repo` only: item 4(c) is carried to a later step by the owner's
ruling (E15 lane contract A3; no claude CLI flag fences what an executed test writes).

## 13. The seeded families

`evals/seeded-cases/`: V1 the gate, V2 base and scope, V3 the cold packet, V4 independence and
verification, V5 the word, and T1 no v1 import (the E15 lane contract section 12), each with one clean case.
The facts are observed through this core's CLI by `evals/seeded-cases/lane_observe.py`; the outcomes live
in an answer key outside this repository.

## 14. What this core never does

It never fixes anything, never touches the build doc, a card or `REVIEW.md`, never writes a records event,
never writes a second verdict doc or edits an earlier block, never pushes, merges or opens a pull request,
never runs `git worktree` or a git command that changes a branch, an index or a worktree, never summons a
reader or launches a harness from a script, never reads a v1 skill's files, and never puts `authorized` on
a Claude row or on a row the owner's answer in this run did not name.

## 15. Interface

### Commands

| Command | At phase | Moves to |
|---|---|---|
| `check-input` | (none) | `checked` |
| `gate` | `checked` | `gated` |
| `ask` | `gated`, `asking` | `asking`; with `--answer`, `asked` |
| `scope` | `asked` | `scoped` |
| `request` | `scoped` | `requested-local` |
| `request --resend` | `requested-local` | `requested-local` |
| `record-local` | `requested-local` | `recorded-local` |
| `request --outside` | `recorded-local`, with the local receipt holding | `requested-outside`; `recorded-outside` when every named row was dropped at suggest |
| `record-outside` | `requested-outside` | `recorded-outside` |
| `verdict` | `recorded-outside`, or `recorded-local` with no outside row named | `verdict-written` |
| `report` | `verdict-written` | `done` |
| `identity`, `skill-identity` | any time | (none) |

### Runtime

`/usr/bin/python3` 3.9 or later, standard library only, with two declared exceptions (the E15 lane contract section
3 and A13). (1) `jsonschema==4.25.1` through `uv run` (PEP 723, `references/back-loop.md` section 2): a command run
without it exits 3, and `--help` and every argument check work without it. (2) The CommonMark reader of the second
reading (section 5, "Two readings"): `markdown-it-py` 3.0.0 and `mdurl` 0.1.2, both MIT, pure Python, vendored
inside this core under `scripts/vendor/` (each package unpacked from its wheel unmodified, its license files kept in
its `.dist-info` folder; the wheel's other metadata left out and named), pinned by `scripts/vendor/VENDOR.json` (each
wheel's file name and sha256, equal to PyPI's published digests, and every vendored file's path and sha256) and held
there by `scripts/tests/test_vendor.py`. Nothing is installed and nothing is fetched at run time:
`vertical_core/commonmark.py` is the only module that imports it, putting `scripts/vendor/` first on `sys.path` for
that one import and restoring the path at once, with the reader's optional `linkify_it` import blocked; a reader
that does not load from `scripts/vendor/` at the pinned versions is a damaged package (exit 1). It runs the same
under `/usr/bin/python3` and under `uv run`.

### Run-directory artifacts

`input.json`, `checkpoint.json`, `selection-build.json`, `gate.json`, `ask.json`, `scope.json`,
`packets/<name>/` (the previews: the material until the verdict or a stop, then `mandate.md`, `files.json`,
`withheld.json`), `summons/<call id>/` (each call's fresh copy, the same shape), `requests/<call id>.json`,
`requests-local.json`, `requests-outside.json`, `readers/` (readers' own), `local.json`,
`local-receipt.json`, `outside.json`, `verdict.json`, `trace.jsonl`, `chat.md`, `result.json`.
