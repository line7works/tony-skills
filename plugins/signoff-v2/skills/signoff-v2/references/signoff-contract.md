# Signoff v2 core: behavioral contract

What this station does, what it may write, what stops it, and the words it uses for a state.
Written for E13 slice 2 of the skills v2 rebuild, against the stations E13 lane contract
(section 10) and its amendments A3 to A6. The slice 2 fix round (amendment A6) changed sections 1,
5, 8 and 9 after Astra's review of slice 2; each change names her finding (F3, F4, F6, F7, F8, F12,
F16). The last fix round of that review loop (after her recheck) changed section 5 again for her
N1 and F7's remainder. Where this document and that contract differ, the contract is
the authority and this document is the defect.

Nothing this station DECIDES is new (ruling E13-1, owner pick P5): v1 signoff's steps, its
severity-to-verdict mapping, its independence rule, its stop rules and its `REVIEW.md` sheet are
carried over. What is new is that the deterministic half is a script rather than prose, and that
the findings are kept in the records component instead of in Markdown alone.

Contents: 1 Job · 2 Inputs · 3 The source set · 4 The review packet · 5 Independence ·
6 Evidence · 7 Severity to verdict · 8 Authorized writes and the recording transaction ·
9 Failure handling · 10 Report-only · 11 Status vocabulary · 12 What is out of scope ·
13 The repo's inspection sheet · 14 Interface.

## 1. Job

A slice has been built. Before it counts as done, an engineer **who did not write it** inspects
it against its spec and either signs the card or writes a punch list.

The reviewer judges the code. This station never does (ruling E13-4): it validates the input,
computes the source set and the identities, builds the review packet, withholds what the
reviewer must not see, talks to the records component, applies the severity mapping, validates
the result and renders. What the reviewer concluded is recorded with who concluded it.

**The anti-rubber-stamp rule, kept from v1.** A review that returns no findings must state what
it tried to break and failed to break. Here that is mechanical: a result with no raised findings
carries a non-empty list of the checks the reviewer executed, each with its output, and an empty
list is a validation failure of the result rather than a clean verdict. "No raised findings" is
counted AFTER the findings are partitioned into raised findings and notes (Astra's F16): a review
whose only findings sit outside the source set raises nothing, so it is a clean review for this
rule and is refused `answer_invalid` at `record-answer` when it lists no executed check. The
proposed completion is validated before `record` writes anything, so a result the validator would
refuse never reaches the log, the document or the card.

**The model floor, kept from v1.** Reviewers run at Opus-class or better. The floor is passed to
`readers` as `floor: opus` with this session's own model id as `session_model`; it is never
assumed and never silently upgraded. A floor this run cannot establish is a stop, not a default.

## 2. Inputs: one validated structure

One input per run, `references/input.schema.json`, every object closed. Accepted and rejected
examples sit in `references/examples/`, and `scripts/validate-examples.py` checks both sets and
drops each required field of every accepted example in turn.

Caller values are bound as data — argv items and files — and never pasted into shell text.

Three checks a schema cannot make are path rules, and each is a named stop rather than a schema
error: the run directory is outside the workspace; the workspace exists; the build doc stays
inside the workspace after symbolic links are resolved.

The phases, in order, each one CLI command:

| Phase | Does | Writes |
|---|---|---|
| `check-input` | schema, path rules, the component's reachability | the run directory, `input.json`, `state.json` |
| `scope` | the source set, the identity, the packet; levels the log as a dry run | `packet/` |
| `request` | the `readers` request and the reviewer's mandate | `request.json`, `readers/mandate.md` |
| `record-answer` | the evidence rules, raised against note, the severity mapping | `answer.json` |
| `record` | the recording transaction | `receipt.json`, then the project's records |

`identity` and `skill-identity` return their objects and write nothing.

## 3. The source set

The set a review covers is computed from git, never guessed, and it is three lists plus the base
(lane contract section 8):

- **committed**: `git diff --name-only <base>..HEAD`
- **changed**: `git diff HEAD --name-only`, staged and unstaged alike
- **untracked**: `git ls-files --others --exclude-standard`

The base arrives in the input as a ref. A set that cannot be computed — no git work tree root, a
base that does not resolve — is a stop with a reason, never an empty set.

`docs/records/` is excluded from all three (CR-3), exactly as the records component excludes it
from the identity: the component's log describes the source and is never part of it. Ignored
files are in no list.

A defect can hide in any of the three. A file committed since the base but clean in the work
tree appears in no `git diff` against HEAD; an untracked file appears in no diff at all. Both are
in the set, and both are in the packet.

## 4. The review packet

Built by script under the run directory. Two things come out of it, and the difference between
them is the independence rule.

**The file list** carries every path of the source set, once, with the list or lists it came
from, its size and its hash. A path in the set and absent from the list is a stop
(`packet_incomplete`): the run never reviews less than the set and never quietly says it did.
Nothing leaves the list by being called notes.

**The delivered material** is the bytes the reviewer reads: the source under review and the
slice's specification, and nothing from the builder's conversation. What is withheld is still
NAMED in the material, so the reviewer knows a file exists and was kept back rather than
believing it was never there.

**Entries have lstat semantics** (Astra's F7). An entry's size, hash and delivered bytes are the
bytes the entry IS: a regular file's content, and for a symbolic link its link target text, the
bytes Git records for it. A link is never followed, and its referent is never presented as the
tracked file's contents; the entry carries `link_target`, and a referent inside the source set is
reviewed as its own entry. Before anything is recorded, every entry's content identity is computed
again the same way and compared with the packet's; an entry that moved is a `stale_source` stop
that names it (section 8). The records component's identity rules are unchanged: its identity has
always hashed a link as its target text, and the packet now agrees with it.

## 5. Independence

The session that wrote the code cannot review it. It knows what the code MEANT to do and will
read intent into what is on disk.

- The request the reviewer receives carries the packet and the mandate and nothing from the
  builder's conversation: no reasoning, no justification, no account of what was built and why.
- When the input marks the reviewing session as the building session, no reviewer is summoned —
  no mandate and no request file are written — and the answer is REFUSED
  (`refusal_reason: independence`). No verdict is recorded.
- The run records which route ran and the model it observed, never one it assumed.
- **The building session is a recorded harness fact** (Astra's F4, send-back 1). The adapter's
  helper fills `sessions.building` only from the selected build run's own `result.json`, bound to
  this review's workspace, document and slice, and only from that result's
  `invocation.session_id`: the session the build adapter read from the harness record, which the
  build core holds the answer's copy to. A selected result without it is REFUSED by the helper
  (exit 3, `unavailable provenance`, no invocation emitted; Astra's N1), because a null building
  session reads as a different session and would let the building session sign off its own work.
  The recorded id is stripped first, and a blank one is the same refusal (punch2-NEW-4). Both
  harness records define a session id as a UUID, which names one session in either letter case:
  the helper emits an id that reads as a UUID in its canonical lower-case form, and when it is the
  reviewing session's UUID it emits the reviewing id itself, so the core's comparison (byte for
  byte, unchanged) refuses the run on independence. Only a run with no selected build result carries `sessions.building: null`, reported as
  unavailable provenance. The executor's typed `answer.session_id`, and any typed session, never
  stand in for it.
- **The model floor is enforced here** (Astra's F5; v1 Step 0, unchanged under P5). The session's
  model is the adapter's observed `invocation.model.id`; the core computes its class with the
  adapters' own map (`claude-opus-*`, `claude-fable-*`, `claude-mythos-*`, and the provisional
  Codex ids `gpt-6-astra`, `gpt-5.6-sol`, are Opus-class; `claude-sonnet-*` and `claude-haiku-*`
  are below; anything else is unknown) and checks the input's `floor_class` and `floor_met`
  against it, never in its place. `request` emits no reviewer request, `record-answer` accepts no
  answer and `record` records nothing unless the floor is met: a false, null, missing or
  unestablished floor, or typed floor facts that disagree with the id, is a `stopped` result with
  `stop_reason_code: floor_refused` and no project-record write. The reviewer's model is the
  readers result (the answer's `model`, readers' effective model through the adapter's sidecar map):
  it must be established, at the floor, and the session's recorded model, since a `claude-session`
  reader inherits it; otherwise the answer is refused (`refusal_reason: floor`). Nothing upgrades a
  model and nothing changes who is eligible. The result's `floor` block says which facts were used
  and where they came from. **Synthetic replay facts** (a seeded case replays a recorded answer and
  no harness observed a model) enter through one explicit test interface only:
  `SIGNOFF_TEST_REPLAY_MODEL=<id>` under `SIGNOFF_TEST=1`, used where the input or the answer
  carries no model, and named as synthetic in `floor.source`; outside test mode it is ignored.

**What counts as the builder's conversation**, three rules, all declarations rather than guesses
about prose:

1. any path the input's `review.builder_conversation` list names;
2. any path whose file name declares itself the builder's notes — the name, lower-cased with
   separators and the extension removed, holding `buildernotes` or `buildnotes` — or whose first
   Markdown heading says so. The first heading is the first ACTUAL Markdown heading after any
   frontmatter (a leading `---` block to its closing `---` or `...`), leading blank lines and
   fenced code passed over, with no line cutoff; only that first heading is tested (Astra's F9).
   A heading is read by CommonMark's block rules (punch-F9): an ATX heading (`#` to `######`, then
   a space or the line's end) indented up to three spaces, its closing `#` sequence dropped; a
   Setext heading (a paragraph's text lines followed by an `===` or `---` underline indented up to
   three spaces); a fence is three OR MORE backticks or tildes indented up to three spaces and is
   closed only by a fence of the same character at least as long, so a four-backtick fence is not
   closed by three; four spaces of indentation are code, never a heading; a raw HTML comment
   (`<!--` to `-->`) or `<script>`, `<pre>`, `<style>`, `<textarea>` block is passed over like a
   fence; `#word` is no heading. A text that opens with a closed `---` block is read both ways,
   as frontmatter and as a thematic break (where a line before its closing `---` is a Setext
   heading), and a declaration in either reading's first heading counts, so neither can hide one;
   an opener that never closes is not frontmatter. Before the walk (punch2-F9) CRLF and bare CR
   line endings are read as LF and a leading byte order mark is dropped. Block quotes (`>`) and
   list items (`-`, `+`, `*`, `1.`, `1)`) are containers: a line inside one never ends a top-level
   paragraph as a Setext underline, so a `---` after a list item or a block-quote line is a
   thematic break; a lazy continuation line (one that starts no block) stays in the container;
   a line that starts a block leaves it and is read at the top level. A list item or a block
   quote interrupts a paragraph by CommonMark's rules (an empty item, or an ordered one not
   starting at 1, does not); that restriction holds only where the paragraph itself is the
   innermost block the line continues, so on a line that a list item or a block quote does not
   continue, such an item starts a new list and what follows it is read from there (punch3-F9).
   A list item begins with at most one blank line: an empty item followed by a blank line ends
   there (punch3-F9). All seven kinds of raw HTML block are passed over whole: `<script>`,
   `<pre>`, `<style>`, `<textarea>` to any of their end tags; a comment to `-->`; `<?` to `?>`;
   `<!` and a letter to `>`; `<![CDATA[` to `]]>`; a CommonMark type-6 tag (`<div>`,
   `<details>`, `<section>` and the rest of that list, opening or closing) to the next blank line;
   and any other complete tag alone on its line to the next blank line, where it does not
   interrupt a paragraph. The first five kinds end on the first line that holds their end marker,
   the start line included, so `<!-->`, `<!--->` and `<?>` close on their own line (punch3-F9). A
   link reference definition, on one line or over several (its destination, and its title, may
   start on the next line), is read two ways, and either reading's first heading counts: as a
   block of its own, which may take the next line as its destination (so `[a]:` over `===` is a
   definition and no heading), and as the opening lines of a paragraph, set aside when a Setext
   underline arrives (so `[a]:` over `===` is a heading whose text is `[a]:`) (punch3-F9). Both
   readings take time linear in the file's length: the lines a definition may run over are found
   once for each run of them, and each definition is read in place, as far as it runs; what is
   withheld is unchanged (punch4-C3-1). Not
   read as headings, and why: a heading inside a block quote or a list item, and an HTML `<h1>` to
   `<h6>` element (the rule speaks of the first Markdown heading; the file-name rule and rule 1
   still reach such a file). Also left out of the walk: tab stops inside a block-quote marker
   beyond the first.
   A symbolic link is never followed to find one;
3. inside the ledger document, the sections v1 Step 2 names as the builder's and the inspector's
   working records (`## Build assumptions`, `## Deviations`, `## Discovered`, `## Handoffs`,
   `## Punch list`) and every `Status:` line.

An untracked builder-notes file is IN the source set and IN the packet's file list, and its
CONTENT is withheld — both, in that order (amendment A3 item 2). Builder claims planted in the
ledger document's own sections are the same: listed, withheld, never evidence. A finding or a
verdict that quotes withheld text is refused (`refusal_reason: independence`).

**Provenance, over the whole answer** (Astra's F4). The packet's knowledge of which paths are the
builder's conversation reaches the answer check. Every string of the answer — the prose, the
verdict, every finding and kept note, and every `checks_executed` entry's name, command and
output — is refused as `independence` when it: cites a builder-conversation path (its workspace
path, or its file name when no delivered file shares that name, case-insensitively, `:line` or
not); cites a withheld ledger section (`<doc>#<section>`); quotes a span (in `"…"`, `'…'`, `` `…` ``
or `“…”`, 12 or more characters) that appears in the withheld material and nowhere in the
delivered packet; or repeats a withheld line of 24 or more characters verbatim. The last rule is
the older one and stays; it never stood in for citation provenance.

**Citations are resolved before they are compared** (Astra's F3). Every token of every answer
string that could name a path — a Markdown link destination, an angle-bracket link, a `file://`
URL, or any run of path characters — is resolved lexically to a canonical workspace path before
the comparison above: percent encoding is decoded, a `file:` scheme, a query, a `#fragment` and a
`:line` suffix are split off, `.` and `..` segments are normalised, and an absolute path is taken
relative to the workspace (its literal or its real path). A relative path that climbs out of the
workspace is joined to the workspace (its literal, then its real path) and normalised, so one that
comes back in by the folder's own name (`../workspace/builder%20notes.md`) lands on its workspace
path (punch2-F3); an absolute path is normalised the same way before it is taken relative. A path
outside the workspace resolves to nothing, and nothing is read to resolve anything. A resolved path equal to a withheld path (or, as
before, a bare file name no delivered file shares), or a resolved `<ledger doc>#<section>` naming a
withheld section, is the same `independence` refusal, before any verdict or finding is written.

**The tokens follow CommonMark's link grammar** (punch list, punch-F3). A link or image
destination is read the way CommonMark reads it, never by one regular expression: an
angle-bracketed destination may hold spaces (`[source](<./builder notes.md#proof>)`), a bare one may
hold balanced or backslash-escaped parentheses (`docs/builder-notes\(1\).md`), and its optional
title (`"…"`, `'…'`, `(…)`) is scanned again as text. Also tokens: a link reference definition line
(`[n]: <./builder notes.md> "t"`, so a reference-style `[x][n]` is caught at its definition); a
`<…>` token with or without spaces, `file://` included; an HTML `href` or `src` value in any
quoting; a quoted span; and a run of path characters holding backslash-escaped characters (a
shell's `builder\ notes.md`). Backslash escapes and HTML entity references (`&#32;`) are undone as
CommonMark undoes them, `%20` and every other percent escape as before. A withheld path that holds
a space is also looked for in plain prose: each occurrence of its file name, joined with the run
of path characters around it, is resolved the same way, so `./builder notes.md:2` or an absolute
path with a space is caught without any markup. Every tail of the withheld path that holds a space
is looked for, not only its file name (so `./my docs/log.md` is caught), and each of its spaces also
matches a line break with the blanks around it, and a backslash right before the line ending (a
Markdown soft or hard line break renders there, so a withheld path broken at its space, its first
half ending one line and its file name opening the next, is the same citation, punch2-F3; the
backslash hard line break, punch3-F3). A delivered file with a space in its name, cited the same
ways, is still accepted.

Blueprint's `Out of scope:` and `Not in this slice:` lines ARE spec and are delivered.

**Until v2 signoff is itself qualified**, the plan's words hold: initial inspection in this
program still comes from the independent temporary reviewer.

## 6. Evidence

A finding is recorded only with all four of a location inside the source set, a claim, a
scenario, and an evidence kind (`executed`, `read`, `reasoned`).

- One missing REFUSES THE WHOLE ANSWER (`refusal_reason: answer_invalid`): nothing is raised, no
  verdict is recorded, and the answer is neither acted on nor repaired into shape.
- A finding whose location is outside the source set is kept as a NOTE, not raised, and so is
  anything the reviewer itself kept in `notes_kept`. A note never moves the verdict.
- A plausible defect that the reviewer's own execution disproved stays where the reviewer put
  it. This station records what the reviewer concluded; it does not re-judge the code.

## 7. Severity to verdict

v1's table, unchanged (pick P5), over the RAISED findings:

| Severity | Meaning | Effect |
|---|---|---|
| BLOCKER | spec requirement unmet, or a defect that loses data, corrupts state, or breaks a shipped feature | cannot sign |
| MAJOR | real defect with a concrete failure path, contained and fixable in place | conditional |
| MINOR | rough edge, missing guard, thin test | punch list only |

- **signed off** — no BLOCKER and no MAJOR.
- **signed off with conditions** — no BLOCKER; the named MAJORs are fixed before the next slice.
- **rejected** — one or more BLOCKERs.

The mapping is arithmetic over severities, not a judgement about code, so the core computes it.
What the reviewer stated is recorded beside it and a disagreement is reported, never silently
resolved. A refused run records no verdict at all.

The card carries the same three words into the slice's `Status:` line.

## 8. Authorized writes and the recording transaction

The complete list. Anything else is a boundary violation the result must report.

1. The run's own artifacts under the run directory: `input.json`, `state.json`, `packet/`,
   `readers/mandate.md`, `request.json`, `answer.json`, `receipt.json`, `receipt.log`,
   `result.json`, `chat.md`.
2. The document's log under `docs/records/`, through the component's CLI and never directly.
3. One review block at the ledger home's tail in the build doc (Appendix A), never editing an
   earlier entry.
4. A copy of that block in the slice's verdict doc under `docs/reviews/`.
5. The slice's `Status:` line.

**Signoff never clears a finding.** No `disposition`, no `waived`, no `reopened`. Recheck does.

The order, and what each step promises:

- **The Appendix A stop check first** (Astra's F12). Before ANY levelling, the document's
  hand-written records are read with Appendix A's stop check, unchanged: the recheck pilot's own
  reader (`scripts/signoff_core/record_grammar.py` is the pilot's `recheck_core/ledger.py` byte
  for byte, held equal by a test), used as a detector only and never as a source of records. A
  line it cannot place stops the run `missing_input` (`legacy_ambiguous`) with the document, the
  line and its bytes (`unplaced`), and nothing is written. The importer's tolerant success does
  not authorize proceeding. **A line the component itself rendered is not hand-written** (Astra's
  N1): records keeps a ranged location on the review line it renders (A7's F9), which Appendix A's
  grammar has no shape for, so the unchanged check stopped the next signoff on a previous
  signoff's own line. When the check finds anything, this station asks the records CLI which lines
  the component rendered (`import-legacy --dry-run`'s `native_rendered`, `events`, and
  `render --run-id` per native run; never the log), matches each rendered line once, in file order,
  to a byte-equal document line under a heading of its kind and slice, and sets those lines aside
  only when their count, plus the `Status:` lines equal to their slice's last native card, equals
  `native_rendered`. The unchanged check then reads the rest. A hand-written ranged line and a
  second copy of a rendered line still stop `legacy_ambiguous` before any write
  (`scripts/signoff_core/native_lines.py`, the build core's file byte for byte).
- **Level the log (CR-1).** v1 signoff writes findings into the Markdown by hand, so a document
  can be ahead of its log. Every phase that reads the document's records runs `import-legacy`
  first — a dry run for a read-only command, the real thing before a write. The importer reads
  hand-written records more loosely than the pilot's stop rule and refuses an orphan clearing
  line, so this station stops on ANY signal it gives: `legacy_unparsed` above zero in a dry run,
  exit 5, or any refusal (amendment A3 item 3). It does not build a second record grammar.
- **Pin the reviewed identity** (Astra's F3). `scope` pins, beside the packet, the six-field
  identity the component computes for the workspace. At `record`, before the first project-record
  write — the levelling is one — the identity now must equal it. A mismatch is source the review
  never saw: the run ends `stale_source` (`source_moved`), reports both (`source_identity` is the
  reviewed one, `identity_now` the other), and writes no project record. Every event this run
  appends carries the REVIEWED identity; the identity now never stands in for it. A refusal of
  `identity` at either phase is a named stop with a result (`identity_refused`, Astra's F7), never
  a traceback. On recovery only the run's receipted changes are allowed: the receipt pins, when it
  is created, the identity with the run's own targets left out, and a recovering pass that finds
  anything else moved ends `stale_source` too. This station's OWN identity computations on the
  record path (the receipt's guard, the masked identity a recovering pass compares, the guard
  check before the document writes) end the same way when git cannot answer (Astra's F7
  remainder): `recording_failed` (`identity_refused`), with what the receipt already holds, and a
  later `record` settles the run.
- **Pin the source for review, and check it after the last append** (Astra's F2). `scope` also
  pins the identity with exactly the run's own document targets left out (the ledger document and
  the verdict doc it would write), with the packet's entries. `record` compares the source now,
  minus exactly those targets, with that pin: before the first write, on every recovery pass, and
  again AFTER THE FINAL APPEND, just before the receipt is committed. Anything that moved (a file
  that arrived while the card event was being appended included) is source the verdict never saw:
  the run ends `stale_source` (`source_moved`), names the moved paths, reports every append and
  document step that already landed from the receipt, records no verdict and never returns
  `completed`; a new packet and a new review are required. A recovering pass reaches the same stop.
  Every packet entry's content identity is verified in the same checks (section 4).
  **What landed is asked of the log, per append, before any stop is delivered** (punch list,
  punch-F2). A recovering pass that stops before its settle step would otherwise report only what
  the receipt already held as landed: after a kill during the card append, the card event is in
  the log while the receipt still says `unknown`. So every append the receipt holds as `unknown`
  is looked up through the records component (`records.py events` for this run's events of that
  kind, `verify` for the head; argv only, read-only). One the log holds moves in the receipt from
  `unknown` to `landed` (marked recovered) and is reported under `records.appended` with the log's
  seqs; one it does not hold is reported under `records.not_landed` as `absent` (or `unreadable`
  when the log could not be read back) and stays an intent in the receipt. The stop's reason names
  both. Nothing is appended by that question, and the stop being delivered (`stale_source` above
  all) is unchanged.
- **Pin the head.** The head the run read its state against is pinned at `scope`. At `record`,
  BEFORE this run's own levelling, the log must still be at that head; an event another writer
  appended between the two phases is a named conflict before any append. The comparison is taken
  before the levelling precisely so CR-1's own import events are never the ones it flags.
- **Append the findings**, one batch, `--expect-head` the pinned head, all or none: one
  `finding_raised` per raised finding, carrying the slice, the location, the claim, the
  scenario, `raised_by`, and `actor` with this station's name and the run id.

  **`raised_by` carries the slice and nothing else.** It is interface version 1's field and
  Appendix A's fifth one — "which slice's review found it" — and neither moves in this step
  (E13-1). WHO reviewed is recorded elsewhere and joined to the event by the run id:
  `actor.run_id` names this run, and this run's result (`reviewer`: the session, the route, the
  model observed, whether it was independent) and its verdict doc name the reviewer. That is
  ruling E13-4's "recorded with who concluded it" without the record line carrying a field it
  was never meant to carry.
- **Render, place, mirror.** The block is the COMPONENT's rendering (ruling E13-3): since
  amendment A4, `render --run-id R` returns `review`, one block per slice this run's
  `finding_raised` events name, each a heading `### <date> — review: <slice>` and one line
  `- <severity> · <file:line> · (<claim>) · <scenario> · <whose review found it>` per finding.
  The station places those bytes at the ledger home's tail and post-processes nothing — the
  claim's parentheses are the component's reading of Appendix A, and the form its own reader
  round-trips. Signoff clears nothing, so the run can produce no recheck block and no grant; a
  render that carries one is a stop (`unexpected_rendering`), because placing `review` alone
  would silently drop it. A copy goes to the verdict doc, and `mirrors` checks the copy. A
  difference is reported, never repaired.

  **The document levels again afterwards.** `import-legacy` recognises a line byte-equal to what
  `render` produced for a native event the log already holds, counts it under `native_rendered`,
  and never re-imports it — a `Status:` line matching the last card included. So a second
  signoff on one document, and a `/recheck` after one, level the log without a stop.
- **The card**: the `Status:` line, then a `card_set` append under the same receipt pattern, made
  only for a status step that actually landed.

**The receipt.** Each append records its INTENT (the log, the head read at plan time) before the
call and its OUTCOME after. A refusal the component RETURNED is persisted as `refused` — the
exit code, the error, the component's own sentence — before the named stop is delivered, and no
later pass retries it. An unknown outcome (a crash with no answer) is settled against the head
the receipt already names, never against a head read afresh: a head that moved since is a
conflict, not permission. A read that failed is a stop, never an empty set.

**The transaction guard** pins each target's hash beside the source identity before the first
append, so an edit that reaches a target before the document plan exists cannot become that
plan's baseline. Document steps are classified against the VIRTUAL state of each target, so two
steps writing one file do not collide; a hash matching neither the planned state nor the virtual
one is an outside edit and stops the run.

**Every completed target is checked again** (Astra's F6). At the end of the document steps, and
again just before the receipt is committed — on a first pass and on recovery alike — every target
whose steps are all done must hash to the planned hash after its last step. An edit that reached
it after this run wrote it, in a crash window or between the write and the card append, ends the
run `recording_failed` (`outside_edit`) and is left exactly as it is. Once the plan exists the card
is reported from the RECEIPT (its planned `before` and value, `moved` only when its step is done),
never from bytes read afresh, which on recovery already carry this run's own value.

**A partial failure is reported from the receipt** (Astra's F8). A `recording_failed` result lists
every append the receipt holds as landed, with its seqs; every document step with its state
(`document_steps`); the verdict doc the plan authorized (`verdict_doc`); the card as far as it got;
and the failing command's exit, error and name (`records.records_exit`, `records_error`,
`records_command`) with its sentence as the stop reason. It validates and exits 10. A write that
landed is never reported absent, and a refusal the component returned is never retried: a second
`record` re-delivers it.

**The hand-off to recheck needs the verdict mirror tracked** (E13 full review, Astra's F8; a
documented qualification gap, not a behaviour change). This station writes the verdict doc under
`docs/reviews/` and never commits it. When `/recheck` follows on the same document with no commit
between, the recheck pilot updates that authorized mirror and its boundary check reads the change
to untracked content as a violation: the recheck ends `not_clear` and the card stays at this
station's verdict, although the log records the finding fixed. E13 does not qualify that
no-commit hand-off; the precondition is that the mirror is committed before `/recheck`. Nothing here
stages or commits files for the user, and any runtime change to the pilot's decision waits for the
owner's E13-1 ruling (the pilot contract's section 9, "The station loop";
`plugins/recheck-v2/skills/recheck-v2/scripts/tests/test_full_fix_f8.py`).

**Rerunning `record`** settles the run rather than repeating it: completed steps are never
redone, the append is never made twice, and a committed receipt reports the same completion.

## 9. Failure handling

| Condition | Status | Reason code |
|---|---|---|
| The input fails its schema | — (exit 4 before a run exists) | — |
| A path rule fails | `stopped` | `path_rules` |
| The base does not resolve, or the workspace is not a git work tree root | `stopped` | `base_unresolvable`, `not_a_git_work_tree` |
| The workspace has an initialized submodule | `stopped` | `submodules` |
| A path of the source set does not reach the packet | `stopped` | `packet_incomplete` |
| The reviewing session is the building session | `stopped` | `independence` |
| Any part of the answer cites or quotes withheld builder conversation | `stopped` | `independence` |
| A finding is missing one of its four required parts | `stopped` | `answer_invalid` |
| A clean review lists no executed check, counted after findings outside the set became notes | `stopped` | `answer_invalid` |
| The proposed completion fails the result's semantic checks | `stopped` | `answer_invalid` |
| A record line fits no Appendix A shape | `missing_input` | `legacy_ambiguous` |
| The model floor is not met, not established, or its typed facts disagree with the observed id (at `request` or `record`) | `stopped` | `floor_refused` |
| The answer's reviewer model is below the floor, missing, or not the session's recorded model | `stopped` (`refusal_reason: floor`) | `floor_refused` |
| The source moved after the packet was built | `stale_source` | `source_moved` |
| The source outside the run's own targets moved during the transaction, the final append included, or a packet entry's bytes moved | `stale_source` | `source_moved` |
| The component refused `identity` | per the refusal map | `identity_refused` |
| This station's own identity computation failed while recording or recovering | `recording_failed` | `identity_refused` |
| `mirrors` or `render` refused inside the transaction | `recording_failed` | `mirrors_refused`, `render_refused` |
| The importer reports an unparsed record line | `stopped` | `legacy_unparsed` |
| The importer refuses an ambiguous document (component exit 5) | `missing_input` | `importer_ambiguous` |
| Another writer moved the log between two phases | `recording_failed` | `log_moved_between_phases` |
| An append the component refused (exit 4 or 7) | `recording_failed` | `append_refused` |
| An append the component refused (exit 6) | `stale_source` | `append_refused` |
| A target changed outside this run | `recording_failed` | `outside_edit` |
| A records call this station could not read | `recording_failed` | `log_unreadable`, `history_unreadable` |
| A required reference cannot be loaded | `stopped` | `reference_unavailable` |

Every stop is a terminal status with a reason, written to the run directory, and writes nothing
to the project's records. A refused records call carries the component's own sentence, its exit
code and its error.

## 10. Report-only

`report_only` is a field of the input. In that mode the run writes nothing to the workspace and
nothing to the log, and its result says so: `report_only` true, `writes_none` true,
`verdict_recorded` false, and every listed write inside the run directory.

It is not a dry run that skips the work. The source set is computed, the packet is built, the
answer is adjudicated, and the findings the reviewer raised are named as raised in the result.
Only the recording is withheld.

## 11. Status vocabulary

`completed` · `stopped` · `recording_failed` · `missing_input` · `stale_source`. Every result
carries one, and `terminal_status` reduces it to the neutral pair `completion` or `stop`.

A verdict is recorded only by a `completed` run that is not report-only.

## 12. What is out of scope

- **Fixing.** This station is report-only in the v1 sense: it inspects and records, and the user
  decides what to repair after seeing the verdict. The two files it writes are records, not
  repairs.
- **Clearing a finding.** That is `/recheck`'s.
- **The adapters and the installs.** Slice 3 builds `adapters/` and `setups/`; the seam is left
  open here.
- **Writing `REVIEW.md`.** The core READS the sheet (section 13) and never writes it. v1 writes
  it on exactly two occasions — the first-run render on the user's word, and the second-failure
  append with its `verified:` stamp — and both need a judgement this core does not hold: the
  user's word in the first case, a comparison across earlier verdict docs in the second.
  `SKILL.md` carries both as the executor's steps, so the policy is unchanged and the writes
  stay where a person can authorize them.

## 13. The repo's inspection sheet

v1 Step 1's sheet test is mechanical, so the core does it. A file named `REVIEW.md` is the sheet
only when it carries the template's three headings (`## Passes`, `## Severity bar`,
`## Repo-specific checks`) AND every `## Passes` line reads `- <name>: on` or `- <name>: off`
with an optional parenthetical. Anything else under that name — a human review guide, a sheet
missing a heading, a pass with no on/off — is NOT the sheet: the run uses this skill's defaults
and reports `present but not the kit sheet`. The file is the repo's and is never overwritten.

- A pass name outside the four the template carries (`correctness`, `security`, `accessibility`,
  `data-safety`) is reported as unknown and ignored.
- A pass marked `off` never runs, even at DEEP, and the result names the skip with its reason.
- `spec` and `seams` are the loop's own and are not passes: nothing in the sheet turns them off.
- The sheet's bar is this repo's Meaning column for DEFECTS. Two things stand under any bar: a
  spec requirement unmet is a BLOCKER, and the three verdicts do not change.
- The sheet's passes, bar and repo-specific checks are the REPO's standing sheet, not the
  author's rationale, so unlike the builder's conversation they travel to the reviewer in the
  mandate.

The result carries what the sheet said under `review_sheet`, and the chat block prints v1's
`REVIEW.md:` line from it.

## 14. Interface

This document closes `scripts/signoff.py`'s CLI; this section states it in one place, in tables a
test reads (`scripts/tests/test_interface_document.py` extracts each table below by its heading
and fails when the code, the schemas or this section disagree). Added in E13 slice 3 (lane
contract section 11, last bullet). Nothing here changes what the core does; every row restates
sections 2, 8, 9 and 11, the input schema and the script's own exit table (A7a).

### Commands

| Command | Arguments | Exit codes |
|---|---|---|
| `check-input` | `<input.json>` | 0, 1, 2, 3, 4, 10 |
| `scope` | `--run-dir D` | 0, 1, 2, 3, 4, 10 |
| `request` | `--run-dir D` | 0, 1, 2, 3, 4, 10 |
| `record-answer` | `--run-dir D --answer FILE` | 0, 1, 2, 3, 4, 10 |
| `record` | `--run-dir D` | 1, 2, 3, 4, 10 |
| `identity` | `<workspace>` | 0, 1, 2, 3 |
| `skill-identity` | none | 0, 1, 2, 3 |

Every command also takes `--records-root DIR`, and `--plugin-root DIR` and `--skill-root DIR`
(test only), before or after its name. Exit 0: the phase succeeded and the run continues; 10: the
run reached a terminal status, a completion included; 2: usage; 3: missing dependency (jsonschema,
or the records component missing or at another interface version); 4: validation (the input, or a
result that failed its schema or the semantic checks); 1: anything else.

### Result statuses

| Status | Terminal status |
|---|---|
| `completed` | `completion` |
| `stopped` | `stop` |
| `recording_failed` | `stop` |
| `missing_input` | `stop` |
| `stale_source` | `stop` |

### Invocation fields

The input's `invocation` object, which the adapter's helper fills (`../adapters/README.md`).

| Field | Required | Values |
|---|---|---|
| `mode` | yes | `interactive` or `headless` |
| `caller` | yes | `direct`, or the calling station's name |
| `run_id` | yes | one path segment, single use |
| `run_dir` | yes | an absolute path outside the workspace |
| `run_date` | no | `YYYY-MM-DD` |
| `harness` | no | a string, or null |
| `sessions` | yes | `{building: string or null, reviewing: string}` |
| `model` | no | `{id, floor_class, floor_met}`, or null |

### Run-directory artifacts

Every file and folder this core writes directly under `run_dir` (section 8, item 1, with the one
folder that list does not name: `records/`, where `record` keeps the payload files it hands the
component's `append`).

| Artifact | Written by |
|---|---|
| `input.json` | `check-input` |
| `state.json` | every phase |
| `packet/` | `scope` |
| `readers/` | `request` (`readers/mandate.md`; the Codex reviewer's `readers/calls/`) |
| `request.json` | `request` |
| `answer.json` | `record-answer` |
| `receipt.json` | `record` |
| `receipt.log` | `record` |
| `records/` | `record` |
| `result.json` | the phase that ends the run |
| `chat.md` | the phase that ends the run |
