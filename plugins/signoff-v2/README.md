# signoff-v2

The portable signoff core of the skills v2 rebuild (step E13, slice 2, lane S). It sits beside
the v1 `signoff` plugin the way `recheck-v2` sits beside `recheck`; nothing in v1 changes, and
both are renamed at cutover (owner pick P2).

An independent adversarial review of one built slice, ending in a signed verdict. What the v1
skill did in prose, this does in a script wherever the step is deterministic: the source set, the
review packet and what it withholds from the reviewer, the independence refusal, the evidence
rules, the severity mapping, and the recording transaction against the records component.

**Nothing it decides is new** (ruling E13-1, owner pick P5). v1's steps, severity-to-verdict
mapping, independence rule, stop rules and `REVIEW.md` sheet are carried over. What moved is
where the findings are kept and which half is mechanical.

## Layout

```
.claude-plugin/plugin.json       the plugin, at 0.1.0
skills/signoff-v2/
  SKILL.md                       the portable procedure: v1's steps, with each script call named
  references/
    signoff-contract.md          what each phase does, the authorized writes, the stop rules,
                                 the status vocabulary
    input.schema.json            the one validated input structure
    answer.schema.json           what the reviewer reports back
    result.schema.json           one result per run, with a terminal status for every run
    examples/                    accepted examples, and invalid/ for the rejected ones
  scripts/
    signoff.py                   the CLI phase driver
    signoff_core/                the library
    validate-result.py           schema plus the semantic checks
    validate-examples.py         the examples, both sets, plus a dropped-field pass
    tests/                       the suite
evals/seeded-cases/              the slice 0 cases, unchanged, plus observe.py and RUNNING.md
```

  agents/openai.yaml             the Codex sidecar: implicit invocation OFF (never auto-triggered)
  adapters/                      README.md (the index Step 1 points at); claude-code/ and codex/:
                                 profile.md, invocation.py, reviewer.py, _common.py, tests/
setups/                          README.md; claude-code/ and codex/: install.sh, verify-install.sh,
                                 negative-tests.sh, launch.sh, prompts/, RESULTS.md;
                                 verify-package.py and negative-cases.py shared by both

`adapters/` and `setups/` were added in E13 slice 3. The installed-shape lookup of all three
stations is recorded in `plugins/build-v2/setups/RESULTS.md`, "Three stations, one component".

## The phases

```sh
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py check-input <input.json>
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py scope         --run-dir D
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py request       --run-dir D
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py record-answer --run-dir D --answer FILE
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py record        --run-dir D
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py identity <workspace>
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py skill-identity
```

Exit codes are A7a's: 0 the phase succeeded, 10 the run reached a terminal status (a completion
included), 2 usage, 3 missing dependency, 4 validation, 1 anything else. `--help` and argument
checking work without `jsonschema`. Every response carries `interface_version` and
`plugin_version`.

## How it reaches the records component

Through the resolver and the CLI only, never a log file and never an import
(`plugins/records/references/interface.md`, version 2). `signoff_core/records_client.py` is
`recheck_core/records_client.py` **byte for byte**, and
`scripts/tests/test_records_client.py::TheCopyIsExact` fails the moment the two differ. Because
the copy is exact it carries the pilot's own `STATION` constant and test-hook name; nothing here
reads either, and a test holds that line.

## What it proves

| Claim | Where |
|---|---|
| correct review scope | `tests/test_scope.py`, `tests/test_packet.py` |
| independence | `tests/test_packet.py`, `tests/test_answer.py` |
| evidence-backed findings | `tests/test_answer.py` |
| a clean review lists its checks | `tests/test_answer.py`, `tests/test_seeded_cases.py` |
| report-only writes nothing | `tests/test_report_only.py` |
| the recording transaction and its kill windows | `tests/test_records_transaction.py` |
| the A7a interface | `tests/test_cli.py` |
| the repo's inspection sheet | `tests/test_sheet.py` |
| the block is the component's rendering, and the document levels again | `tests/test_block_form.py` |
| a second signoff on one document, and a `/recheck` after one | `tests/test_after_signoff.py` |
| every seeded case, at contract level | `tests/test_seeded_cases.py` |

## Known open point

One, reported rather than hidden, on a boundary this plugin may not write.

**The importer does not name an unparsed line** (the slice 1 builder's Finding 2, left open by
the owner). Amendment A3 item 3 has this station stop on any importer signal, naming the line.
Interface version 1 publishes `counts.legacy_unparsed` as a COUNT with no line number in any
field, and the lines exist only as `legacy_unparsed` EVENTS, which requires a real import, a
write, the opposite of a read-only stop. So the stop names the document and the count, says that
interface version 1 does not name the lines, and points at `records.py survey`. Since the slice
2 fix round (Astra's F12) a line Appendix A cannot place never reaches the importer: the pilot's
own stop check runs first and names the document, the line and its bytes. A line Appendix A
places and the importer still drops in silence is what remains open.

## The slice 2 fix round (Astra's review, amendment A6)

What changed in behaviour, each with its tests in `scripts/tests/test_fix2_astra.py`:

- **F3** `scope` pins the reviewed identity beside the packet; `record` compares the identity now
  before the first project-record write and ends `stale_source` (`source_moved`) with both on a
  mismatch. Every event carries the reviewed identity. Recovery allows only the run's receipted
  changes.
- **F4** builder-conversation provenance reaches answer validation: a citation of a builder-notes
  path or a withheld section, or a quotation found only in withheld material, anywhere in the
  answer (`checks_executed` included) is refused on independence.
- **F6** every fully completed target is checked against its final planned hash at the end of the
  document steps and before commit; an outside edit is `recording_failed/outside_edit` and is left
  intact; the card is reported from the receipt.
- **F7** a refusal of `records.py identity` is a named stop with a result (`identity_refused`).
- **F8** a `recording_failed` result is built from the receipt (landed appends, `document_steps`,
  the authorized verdict doc, the card as far as it got, `records_command`) and validates, exit 10.
- **F12** Appendix A's stop check before any levelling (`missing_input`, `legacy_ambiguous`,
  `unplaced`): `signoff_core/record_grammar.py` is the pilot's `ledger.py` byte for byte.
- **F16** the clean-review check runs after findings are partitioned; `record-answer` refuses a
  review that raises nothing and lists no check, and `record` validates the proposed completion
  before writing anything.

## Closed since round 1

Kept here because the README used to carry them as open.

- **The review block is the component's rendering** (records amendment A4): `render` returns
  `review`, and a document this station wrote levels again. `import-legacy` recognises a line
  byte-equal to what `render` produced for a native event the log already holds, and reports it
  under `native_rendered` instead of reading it as a second raise.
- **A `/recheck` starts on a finding this station raised** (pilot contract Revision 8, E13
  CR-F3). A natively raised finding carries no document line of its own; the pilot now addresses
  it where the component's rendering of it sits in the document, under the heading it actually
  sits under. `tests/test_after_signoff.py` drives `recheck.py start` after a signoff and asserts
  the accepting path outright: one checklist item, the reviewer's location and claim, the
  document's `### <date> — review: Slice <X>` heading, and the run handed to `verify`.

## Provenance

Built in E13 slice 2 against the stations E13 lane contract (section 10) and its amendment A3.
The seeded cases under `evals/seeded-cases/` were written in slice 0 by an agent that built
neither core; their expected outcomes live in an answer key this lane never saw, which is why
`observe.py` emits facts and never an expectation.

## Fix round (E13 full review: Astra's F2, F3, F4, F5, F6, F7, F9; control-room CR-1)

What changed in behaviour, each with its tests (red first; the red output is in the round's
scratch folder):

- **F2 (BLOCKER)** `scope` pins the source for review with exactly the run's document targets left
  out (the build doc and the verdict doc it would write). `record` compares the source now, minus
  those targets, with that pin before the first write, after the FINAL append (just before the
  receipt commits) and on every recovery. A file that arrived during the card append was recorded
  as `completed / verdict_recorded true`; it is now `stale_source` (`source_moved`), naming the
  path, with the landed appends and document steps reported from the receipt and no verdict.
  `scripts/tests/test_full_fix_signoff.py` `F2...`.
- **F3 (MAJOR)** every answer string's citations are resolved lexically to canonical workspace
  paths before the withheld-provenance comparison (`./`, absolute paths, `file://` URLs, percent
  encoding, `..` segments, Markdown destinations, `#fragment` and `:line` suffixes), including check
  commands, outputs and kept notes: a citation of withheld builder material is an `independence`
  refusal. `F3...` in the same module.
- **F4 (BLOCKER)** both adapters' `invocation.py` lose `--building-session`. The building session
  comes only from the selected build run's own `result.json` (`--build-result`), accepted in its
  own run directory and bound to `--workspace`, `--build-doc` and `--slice`; without one it is null
  and `measurement.building_provenance` is `unavailable`. Send-back 1 closed the build side: build-v2's
  input and result carry `invocation.session_id`, the harness-read session its adapters print, and
  the build core stops `session_mismatch` when the typed answer disagrees; these adapters read the
  building session from the result's `invocation.session_id` only, and a result without one is
  unavailable provenance, never a fallback to `answer.session_id`.
  `adapters/*/tests/test_full_fix_f4.py` (class `SendBack1TheHarnessIdentityOnly`).
- **F5 (MAJOR)** the core enforces the Opus-class floor (`scripts/signoff_core/floor.py`): the
  session's class computed from the adapter's observed model id, typed `floor_class`/`floor_met`
  checked against it, the reviewer's model from the answer (readers' effective model) at the floor
  and equal to the session's; `request`, `record-answer` and `record` stop `floor_refused` with no
  project-record write; the result carries `floor`. Seeded replays supply synthetic facts only
  through `SIGNOFF_TEST_REPLAY_MODEL` under `SIGNOFF_TEST=1`, named as synthetic. `F5...` classes.
- **F6 (MAJOR)** the Codex `reviewer.py` carries no transport: it checks the run's readers request
  and stops `lane-unavailable` (exit 3) naming the missing capability (readers has no
  floor-qualified route a Codex session can dispatch), and maps a readers sidecar. The private
  `codex exec` path, its canned test route and the child-rollout fixture are gone; the Codex setup
  no longer turns network on for signoff-v2. `adapters/codex/tests/test_full_fix_f6.py`.
- **F7 (MAJOR)** packet entries use lstat semantics: a symlink is its link target text
  (`link_target`), never the followed referent; every entry's content identity is verified before
  recording and a moved entry is named in the `stale_source` stop. `F7...` classes.
- **F9 (MAJOR)** the first actual Markdown heading after frontmatter decides builder-notes
  classification, with no line cutoff. `F9...` class.
- **CR-1** `SKILL.md` frontmatter carries `disable-model-invocation: true`, the manual-only sidecar
  on Claude Code (`scripts/tests/test_full_fix_cr1.py`). **CR-2**
  `signoff_core/constants.py`'s `KNOWN_RECORDS_VERSIONS = (1,)` is dead: nothing reads it (the
  client copy checks the component's interface version itself), so it was left as it is.

## Punch list (E13, after Astra's recheck: punch-F2, punch-F3, punch-F9, punch-N1)

- **punch-F2 (BLOCKER)** a recovery that stops (`stale_source` above all) first asks the records
  component, through `records.py events` and `verify` (argv, read-only), about every append the
  receipt still holds as `unknown`: a landed one moves to `landed` in the receipt, marked
  recovered, and is reported under `records.appended` with the log's seqs; an absent one is
  reported under `records.not_landed` (`absent`, or `unreadable`). Before, a kill during the card
  append plus a moved source reported only the findings' seq while the log held the card's. A later
  pass that completes still lists such an append under `recovered`. `test_fix3_astra.py`'s F7
  recovery test asserted the old `appended: []` and now asserts the new rule.
  `scripts/tests/test_punch_f2.py`.
- **punch-F3 (MAJOR)** citation tokens follow CommonMark's link grammar: angle-bracketed
  destinations with spaces, balanced and backslash-escaped parentheses, link titles, reference
  definition lines, `<...>` tokens with spaces, HTML `href`/`src`, quoted spans and shell-escaped
  runs, with backslash escapes and HTML entities undone; a withheld path holding a space is also
  found in plain prose. Before, `[source](<./builder notes.md#proof>)` was recorded.
  `scripts/tests/test_punch_f3.py`.
- **punch-F9 (MAJOR)** `packet.first_heading` reads headings by CommonMark's block rules: Setext
  headings, ATX headings indented up to three spaces (closing `#`s dropped), fences of three or more
  backticks or tildes closed only by a fence of the same character at least as long, indented code,
  thematic breaks, HTML comments and raw HTML blocks; a leading `---` block is read as frontmatter
  and as a thematic break, and either reading's first heading can declare the notes. Before, a
  Setext, an indented or a four-backtick-fenced case was delivered and signed.
  `scripts/tests/test_punch_f9.py`.

## Punch list round 2 (E13, after the independent checker: punch2-F9)

- **punch2-F9 (MAJOR, one regression)** the first-heading reader is a small CommonMark block walker:
  CRLF and bare CR line endings read as LF and a leading byte order mark dropped; block quotes and
  list items read as containers, so a `---` after a list item or a block-quote line is a thematic
  break and never a Setext underline (round 1 had turned `- first item\n---\n# Builder notes`,
  withheld at `dfe8919`, into a delivered file); all seven raw HTML block kinds passed over whole
  (type 6 `<div>`, `<details>` and the rest, and type 7, to the next blank line); single-line link
  reference definitions are not paragraph text. Before, the checker's list, quote, CRLF Setext,
  `<div>`/`<details>` and byte-order-mark shapes were delivered and signed. A file whose `---`
  follows a list item that interrupts a paragraph (`Builder notes\n- item\n---`), or whose `===`
  is a lazy line inside a block quote, has no heading in CommonMark and is now delivered where
  round 1 withheld it. `scripts/tests/test_punch2_f9.py`.
- **punch2-F3 (MINOR)** a withheld path that holds a space is found in prose when it is wrapped
  at that space onto the next line (a soft or a hard line break), and when the space sits in a
  folder name; a relative path that climbs out of the workspace and back in by the folder's own
  name (`../workspace/builder%20notes.md`), and an absolute one through the parent, resolve to
  their workspace path. A climb out that ends outside the workspace still resolves to nothing.
  Before, the checker's soft-wrapped and climb-out-and-in spellings were recorded.
  `scripts/tests/test_punch2_f3.py`.
- **punch2-NEW-4 (MINOR)** both adapters' `building_from_result` strips the recorded
  `invocation.session_id` and refuses a blank one like a missing one (exit 3); an id that reads as
  a UUID is emitted in its canonical lower-case form, and as the reviewing id itself when it is the
  same session in another spelling, so the core (unchanged, byte-for-byte) refuses on independence.
  Before, `"   "` or the reviewing id upper-cased reached a verdict.
  `adapters/*/tests/test_punch2_new4.py`.
- **NEW-3 (left for the owner)** an untracked reviewed file whose executable bit flips during or
  after the final append still completes: the packet pins content bytes and size, as this
  contract says. Not changed in this round.
- **punch-N1 (look)** the N1 repair checked end to end through both helpers on the S3 case shape
  (a legacy build result from this session, no `invocation.session_id`): exit 3, no invocation and
  no session id printed, the project tree (`.git` included), the build run and the run-directory
  root untouched. No behaviour change: the core's input carries no fact that a build result was
  selected, so it reads `sessions.building: null` as "not known", and the signoff contract (section
  5) puts the refusal of a selected result without an identity on the helper; a test pins that.
  `adapters/*/tests/test_punch_n1.py`.

## Build record (E13 slice 3: adapters and installs)

- Built on 2026-09-23 by one fresh Opus 5.5 builder at high, in-process, in the control room's
  worktree on `feat/stations-e13` from `f62e4b3`, against the lane contract section 11 with
  amendments A1 to A8 and the control room's slice 3 brief. Nothing the core decides changed
  (E13-1, P5); the one `SKILL.md` change is Step 1's pointer to `adapters/README.md`.
- Added: the adapter index; two profiles; `invocation.py` (the whole invocation block: mode, run
  ids, harness, both sessions, the model and its v1 floor) and `reviewer.py` (Claude Code: the
  readers request block and the sidecar map; Codex: one fresh `codex exec` reviewer and its
  identity, REMOVED in the full-review fix round below, Astra's F6) per harness, with their suites (Claude Code 30 tests, Codex 21 at the builder's run,
  the independence refusal driven through the real core in each); `agents/openai.yaml` with
  implicit invocation off; the setups of both harnesses; `references/signoff-contract.md` section
  14 "Interface" and `scripts/tests/test_interface_document.py` (7 tests);
  `scripts/tests/test_installed_shape.py` (route 3b, 2 tests).
- `scripts/tests/test_seeded_cases.py` drives `evals/seeded-cases/observe.py`, which the control
  room runs when it grades; the builder did not run it.
- Test counts, confirmed by the control room on 2026-09-23 under both runtimes (`/usr/bin/python3` 3.9.6
  and `uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3`): `scripts/tests/` 161
  (without `test_seeded_cases.py`), `adapters/claude-code/tests/` 30, `adapters/codex/tests/` 21;
  `validate-examples.py` ok both ways; the thirteen seeded cases graded 13 of 13. The check is filed in
  the Clerk packet (`astra-outputs/e13/reports/slice-3-check.md`).
