# Vertical v2 core: behavioral contract

What this station does, what it reads, what it may write, what stops it, and the words it uses for a
state. Written for E15 slice 1 of the skills v2 rebuild, against the E15 lane contract (sections 6 and
8, amendments A1 and A2) and the control room's readings CR-1 to CR-10 in the slice 1a brief. Where this
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
first and independent; every outside finding verified; `Refuted: N`; re-gradings recorded with a reason;
the repeats and misses against the record; the one write, appended on a rerun; the stop at the verdict;
the `VERTICAL:` block. The reviewer eligibility, counts and test requirements are v1's (owner pick P6):
the local fleet at the Opus floor, the lenses the depth and the inspection sheet select, the outside
rows the owner names.

What moved: the deterministic half is a script; the review mechanics v1 held by deference are stated in
section 6 in this core's own words (ruling E15-6), and the lens briefs in `references/lens-briefs.md`;
the local lenses review a `git archive` copy with no history instead of a detached worktree (A2, Q1);
every packet's spec has the ledger removed and every packet carries a hashed file list and a withheld
list (ruling E15-8); the cards come from the records component as well as the `Status:` lines (ruling
E15-9); every reader summons is a trace line (ruling E15-7).

## 3. The phases

A phase command against a run at the wrong phase is exit 2 naming the command to run instead. Every
phase reads and writes only the run directory, except `verdict`'s one write.

### 3.1 `gate --run-dir D [--doc PATH | --name NAME] [--records-root DIR]`

The doc hunt (ruling E15-10, `station_core/hunt.py`): `--doc` takes the build doc the invocation names
or the plan the session established (an existing `.md` inside the workspace; anything else is refused,
exit 5); else the repo's tiers, lowest tier deciding: `docs/plans/*-<name>.md` and `docs/plans/<name>.md`,
then `docs/<name>-build-plan.md`, then a phase or slice doc (`docs/*phase*.md`, `docs/*slice*.md`,
`plan/*.md`). `none` stops (`selection-none`, ask the owner); `several` stops (`selection-several`, the
candidates listed, none picked).

The slices: every `## Slice <name> <dash> <short>` heading and the `Status:` label inside its section,
read through the build-doc form's parse (`station_core/templates.py`). Zero slices, or a slice with no
`Status:` line, stops (`gate-malformed`); a collapse never passes it.

The cards (reading CR-1): the records component's `state` for the build doc. A slice's card is its
`card_observed` (the last card set or observed in the log); it must equal the slice's `Status:` line
text, and the component's `card_derived` must equal it too, so a log still holding an open finding does
not pass behind a signed card. Either disagreement stops (`card-disagrees`), naming the records' card and
the line. A slice the log names nothing about falls back to its `Status:` line, and `gate.json`'s notes
say so. Every slice must stand `signed off`; a short slice stops (`gate-short`), naming each slice and its
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

The local row is `claude-session` (profile `repo-with-tools`) on Claude Code and `claude-opus-cli` on
Codex, with the profile that row offers (section 12). The outside rows read the export as a workspace
(`repo`) where the row offers it, and a packet otherwise (`packet-only`).

### 3.3 `scope --run-dir D`

Section 5's copies and the packets (ruling E15-8): one per local lens (`packets/local-<lens>/`) and one per
outside row the answer named (`packets/outside-<row>/`), each with its mandate, `files.json` (every file
the reviewer receives, the workspace's and the documents', each with its sha256 and size) and
`withheld.json`, written before any request. A local packet's documents are the spec and, when it is the
kit sheet, `REVIEW.md`; an outside repo row's workspace is the export; a packet-only row's documents are
the export's UTF-8 files staged with every `/` written `__` (a file that is not UTF-8 is left out and named
in the Method line). The outside mandate is `assets/vertical-mandate.md`, v1's byte for byte, its three
slots filled: the spec, the base commit, the boundary lines. Each local mandate is the lens's brief, the
scope, the base and boundary, the ledger-versus-spec line, the repo's checks, and the reporting shape.
Writes `scope.json`, `spec.md`, `REVIEW.md` (a copy, when it is the sheet), `mandate.md`, `export/`,
`local/`, `packets/`.

### 3.4 `request --run-dir D [--readers-root DIR]` (the local fleet)

readers' identity first (section 11). Every local packet held to its file list (each file's sha256, no
file added since): a moved packet is refused (exit 5) and nothing is built. One request per lens, built by
`station_core/readers_request.py`: the local row, its profile, the local copy as the workspace, the spec
and `REVIEW.md` as documents, the lens's mandate, `floor: opus`, `session_model` on `claude-session`, call
id `<run id>-local-<lens>`, `run_dir` `<run dir>/readers`; no `authorized`, `model`, `effort`, `isolation`
or `raw_path`. A Claude Code run with no `station.session_model` is refused. Writes `requests/` and
`requests-local.json`. `--resend LENS --status S` builds the one re-send a lens may take, call id
`<first id>-2`, only after `transport-failed`, `empty` or `incomplete` and only once (exit 5 otherwise).

### 3.5 `record-local --run-dir D --answer FILE`

The answer (kind `local`): the merged findings, each stamped, the method the local review used to verify,
and what each lens tried to break. Each call's status, model, profile, parity, isolation, reason and raw
file are read from readers' sidecar (a call with none is refused). A lens whose last call is not `ok`:
a retryable failure not yet re-sent is refused with the re-send command; otherwise the run stops
(`local-incomplete`), or (`floor-refused`) on a floor refusal. The findings are held to section 6; a
refusal is exit 5 and nothing is written. Writes `local.json` and one trace line per summons.

### 3.6 `request --run-dir D --outside [--row ROW ...]`

Only after `record-local` completed (reading CR-5): before it, exit 5, and no outside request file exists
under the run directory. One request per row the answer named (or the `--row` subset): `authorized: true`,
decided by `station_core/readers_request.py` from the answer's rows and nothing else; refused (exit 5) for
a row the answer did not name, a Claude row the answer named (a Claude row is never an outside reviewer
and never carries `authorized`), a row the ask did not offer, or a row suggest reported dropped (reading
CR-6). A packet-only request carries `output_budget: 32768`; a model id the owner typed rides as `model`.
Writes `requests-outside.json`.

### 3.7 `record-outside --run-dir D --answer FILE`

The answer (kind `outside`): the verified findings and the executor's ledger notes. A call that is not `ok`
is a dropped reviewer, recorded with its status and reason; no finding may be credited to it. Writes
`outside.json` and one trace line per summons.

### 3.8 `verdict --run-dir D [--records-root DIR]`

At `recorded-outside`, or at `recorded-local` when the answer named no outside row. The merge, the count,
the ledger comparison and the one write (reading CR-8): see `scripts/vertical_core/verdict.py`'s rules,
stated in section 6. The doc is found by glob over `docs/reviews/*-vertical-<feature>.md` (`<feature>` the
doc's topic, v1's rule): none, created as `docs/reviews/<date>-vertical-<feature>.md`; one, a dated block
appended at its end with every earlier byte untouched; several, a stop (`verdict-doc-ambiguous`) with
nothing written. A target that is a link or lies outside the workspace's `docs/reviews/` is refused
(`write-refused`). Report-only writes nothing. The copies and the staged files are removed afterwards.
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

**The base** (reading CR-2), v1's precedence: (1) a base the build doc records: a header line, before the
first `## ` heading, reading `Base: <commit>` with the commit as 7 to 40 lowercase hex characters, the
first such line counting; a recorded base that resolves to no commit stops (`base-unresolved`); (2) `git
merge-base <default branch> HEAD`, the default branch being the remote's `HEAD` when one is named, else
`main`, else `master`, and a merge base equal to HEAD itself counting as none (nothing to review); (3) the
owner's base from `station.owner_words.base`; else a stop that asks (`base-unresolved`). The base and how
it was found go in the Method line.

**The boundary** is `git diff --name-status <base>..HEAD` (a rename keeps its old path too). The clean-tree
rule reads `git status --porcelain` against the boundary's paths and the build doc.

**The copies** (reading CR-3; A2, Q1): `export/` and `local/`, two `git archive` extractions of HEAD under
the run directory, with `docs/reviews/`, `docs/records/` and `REVIEW.md` left out and no `.git`: no commit
message, no history. In both, the builder's notes (a file whose name, lower-cased with its extension and
separators removed, holds `buildernotes` or `buildnotes`) are dropped and the build doc's copy is the spec.
A symbolic link in the commit is written as a plain file holding its target text. vertical-v2 never runs
`git worktree`, never runs a git command that changes a branch, an index or a worktree, and removes both
copies after the verdict.

**The spec** (reading CR-4) is the build doc with `## Punch list` and `## Handoffs` (each from its heading
to the next `## ` heading, every block inside) and every slice's `Status:` line removed, through the
build-doc form's parse; everything else stays byte for byte. **The withheld list** of every packet names,
each with why: every tracked file under `docs/reviews/` (a prior verdict) and `docs/records/` (the
records log), the builder's notes, the removed sections and lines with their line numbers, every
untracked and ignored path, every working-tree change; an outside packet also names `REVIEW.md`.

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
| `card-disagrees` | a slice's card in the records disagrees with its `Status:` line or with the component's derived card |
| `records-refused` | the records component refused a read; its own sentence is carried |
| `not-git` | the workspace is not a git work tree root with a commit |
| `base-unresolved` | no base: none recorded, no merge base, none from the owner; or a recorded base that resolves to nothing |
| `dirty-boundary` | dirt touches the boundary or the build doc and the owner gave no committed-state-only order |
| `station-refused` | readers' identity breaks the trace's refusal rule; a `refused` trace line is written |
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
the tree, the depth and lenses, each local lens's row, model and profile, the route, each outside
reviewer's row, model, profile, parity, isolation, anomaly and files left out, each dropped reviewer with
its status and reason, how the local review verified, and what every packet withheld), and `### Unverified
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
(reading CR-9). Before any request, readers' identity is read: the root the shared resolver finds
(`--readers-root`, then route 3a, then 3b), the name and version its manifest carries, and the protocol
version its own CLI prints (`readers.py --version`, which summons no reader). An identity the refusal rule
refuses (a name other than `readers`, a root under a v1 plugin folder, a protocol this core does not know)
stops the run (`station-refused`) with a `refused` line and no request. Every summons, whatever its status,
is a `summons` line with that identity, the route, the readers run directory, its status, call id and row.

## 12. The harness seams

Ruling E15-12 and reading CR-10. On Claude Code the local lenses are `claude-session` calls with
`repo-with-tools`, fresh subagents that may run the project's tests in their archive copy. On Codex they go
through `claude-opus-cli`, the portable Claude row a shell can dispatch, with the profile that row offers:
`repo-with-tools` once readers offers it on that row (the slice 1a brief's item 4(c)), `repo` until then.
On `repo` each lens reads the code and runs no check; the ask says so, the request's route says so, and the
Method line names the route and states "static analysis only". As built, the row offers `repo` only: item
4(c) stopped on its question (the claude CLI offers no flag that confines what a test run writes).

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
| `request --outside` | `recorded-local` | `requested-outside` |
| `record-outside` | `requested-outside` | `recorded-outside` |
| `verdict` | `recorded-outside`, or `recorded-local` with no outside row named | `verdict-written` |
| `report` | `verdict-written` | `done` |
| `identity`, `skill-identity` | any time | (none) |

### Run-directory artifacts

`input.json`, `checkpoint.json`, `selection-build.json`, `gate.json`, `ask.json`, `scope.json`, `spec.md`,
`REVIEW.md`, `mandate.md`, `export/` and `local/` (until the verdict), `packets/<name>/` (`mandate.md`,
`files.json`, `withheld.json`), `requests/<call id>.json`, `requests-local.json`, `requests-outside.json`,
`readers/` (readers' own), `local.json`, `outside.json`, `verdict.json`, `trace.jsonl`, `chat.md`,
`result.json`.
