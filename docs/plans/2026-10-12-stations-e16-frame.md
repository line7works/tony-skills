# E16 frame: the executor's rules, the proof a run may claim, and how a secret travels

Written 2026-10-12 by a new author, on the owner's word (the lane contract
`docs/plans/2026-10-11-stations-e16.md`, section 18, A5), from the outside reviewer's three design
reads. **This document is the single source for the frame.** It replaces Parts 1 to 3 of the
operation catalog (`docs/plans/2026-10-12-stations-e16-operations.md`): the rules X1 to X13, the
evidence classes E1 to E4 and the secret rules K1 to K8 are withdrawn. The owner's rulings (the
contract's sections 5 and 18) stand above this document. This document stands above every lane's
rows: a row that cannot be written under these rules is not written, and the lane stops and asks.
**Status: read once by the outside reviewer (the contract's section 18, A9); this text is after the
one fix round that followed, and her check of that round is not yet done. No slice has the owner's
go.**

How to read it. Part 1 is the governing rule. Part 2 names the words the rules use. Part 3 is the
rules, in nine groups; each rule has one id, is stated once, and is followed by one line saying what
a test on fakes would assert. Part 4 is the risk that is left and who has accepted it. Part 5 is
worked examples, which illustrate the rules and are not a source.

## Part 1. The governing rule

**GOV-1. What the tool cannot prove, it stops on and hands the owner.** It does not guess, send a
create again on its own, take as the project's a thing it found, or record a way back it cannot
prove. Where the rules below are silent on a case, or two of them pull apart, the tool stops; it
never picks. (The owner's ruling, A5.)

Test on fakes: a fake that returns a result kind no rule names, and a journal that holds a status no
rule names, each end the invocation `stopped` with the operation named and with no effect call
recorded after the stop; and in a known kind where a ground of proof is missing (the by-hand
fixtures of EV-1's test line), the outcome is the cell OP-6 names and is never `done`.

## Part 2. Words

These name things. They carry no rule; every rule is in Part 3.

| Word | Meaning |
|---|---|
| run | one summons of sunrise, sunset or restore for one project, from its first look to its end; it has one run directory and one journal |
| invocation | one start of the script working on a run |
| look | the reading an invocation does before any effect |
| thing | anything outside the run directory that a run reads or changes: a folder, a file, a span of text in a file, a repository's branch or tag, a provider's resource, a schedule |
| identity | what makes a thing the same thing later. For a path: the file system's own identity for the object there (the one a rename keeps and a copy does not), with its volume. For a provider's resource: the id the provider assigned, with the account and scope it was read under. For a commit: its address |
| tracked state | the facts about a thing that its row says the run records and later compares, and no others |
| operation | one row of a lane, of one of the nine kinds |
| effect | the one change an operation makes outside the run directory and staging |
| output | the named result an operation provides, with named fields (an id, a path, a commit) that later operations refer to |
| staging | a private folder the run made, where it builds an object before publishing it |
| protected record | a file in the run directory that holds content the run may not show |
| form | a file rendered for the owner to read |
| manifest | the plan of a run: what the preview shows and what execution may do |
| go | the owner's typed word approving a manifest |
| attempt | one making of a check, recorded on its own |
| declaration | what a provider module states beforehand about one command: its arguments, its environment, its inputs and its result |

## Part 3. The rules

### 3.1 Runs, the look, the plan and the owner's word

**RUN-1. Every invocation starts the same way.** In this order: the gate (the vault and machine
checks); the locks (RUN-2); the run directory opened, or made for a new run (RUN-4); the rest of the
look (RUN-5). Nothing comes before the gate, the cue included. A failed gate ends the invocation
with nothing created and no lock taken.

Test on fakes: with no vault, with a stub vault, and with a vault inside a synced folder, the
invocation ends refused, the fixture home is byte-equal to before, no lock file exists and the cue
fake recorded no call; on a sound fixture vault the gate passes and the fakes' records show the
gate, then the lock, then the run directory, then the look's reads, in that order.

**RUN-2. One lock per project key.** The project key is the project's name folded: lowercased, with
every character that is not a letter or a digit removed. An invocation takes the lock of the key of
the name it was summoned with before it reads any thing of the project, and the lock of the key of
every other name form the look resolves for the project on any layer before the manifest is built,
in sorted order. A lock is of the kind the system releases when its holder dies, and is never broken
by age. An invocation never waits for a lock: one that meets a held lock ends at once, names the
run that holds it, and reads nothing more. A file that the runs of other projects also change has a
lock of its own, held only around the one change (OP-3, C3).

Test on fakes: of two invocations summoned with two spellings of one name (a different case, a
hyphen against an underscore), the second ends on the lock with no probe call recorded; of two
summoned with names that fold to different keys, where the first's look resolved the second's key,
the second ends on the lock the same way; the lock fake's record shows the added keys taken in
sorted order and no wait; after the first is killed a third takes the locks and goes on; two runs of
different projects that change one shared file both land their change.

**RUN-3. One open run per project key.** A run is open from its first go (RUN-9) until it ends
`complete`, `ended with exceptions` or `closed` (RUN-12). At the go the run is recorded as open
under every project key its look resolved, in one write that records all of those keys or none of
them, made together with the record of the go; a re-plan that resolves a further key adds it the
same way with its own go. Every summons looks for an open run under the key of the name it was given
and under each key its look resolves, before a manifest is built. While any of those keys has an
open run, the summons may only resume it (RUN-10), re-plan it (RUN-11) or close it (RUN-13); any
other summons is refused and names the open run. The one exception is in EV-7.

Test on fakes: with a sunrise left `waiting` whose look had resolved a second key, a sunset summons
under either key is refused with the open run named and with no read past the lock recorded; a kill
between the go and the opening record leaves the run open under all of its keys or under none; and a
resume, a re-plan, a close and a restore of that run (EV-7) are each accepted.

**RUN-4. The run directory, and the one assumption.** The run directory is a private folder in the
owner's home directory, outside every repository, one folder per run, owner-only, and kept after the
run ends (the owner's ruling, A2). It holds the inputs, every manifest, the journal, the protected
records, the forms and staging. Every proof in this frame assumes that nothing but the run changes a
run directory or a staging folder. The frame checks what it can: at the start of every invocation
the run directory and everything in it must be owner-only and the journal's chain (LOG-1) must hold,
or the invocation stops.

Test on fakes: a run-directory file given wider permissions between two invocations stops the second
before it reads any thing of the project; a byte changed in the middle of the journal does the same;
with the run directory untouched the second invocation passes both checks and goes on.

**RUN-5. The look only reads.** Before the owner's word an invocation changes nothing outside its
run directory. The look reads: the tools on the path and each provider's identity, which is the
account every remote operation will act as; what the harness adapter declares it can do (its
capabilities); the journals of the project key's earlier runs; the planning facts of RUN-6; and the
owner's answers that shape the plan. An answer taken in the look is an input of the run, validated
(SEC-9) and recorded in the manifest. A look that lacks an answer it needs ends the invocation with
the questions listed and nothing approved. Nothing a look read is carried to a later invocation
except through the manifest.

Test on fakes: with every fake recording its calls, a look that reaches its preview records only
read calls, and among them each provider's identity read, the adapter's capability declaration and
the read of the key's earlier journals; it leaves every fake's state, and the fixture home outside
the run directory, byte-equal; a look with an unanswered question ends with the question listed and
no manifest written.

**RUN-6. A planning test reads only what exists before the run.** For each candidate operation the
look makes one planning test. It may read (a) the place where the operation would make a thing, and
(b) a thing that already exists and is to be changed, moved, kept or adopted, read where it is now.
It never reads a thing that an operation of the same plan is to make, nor a state that an earlier
operation of the same plan is to leave. Where an operation depends on those, the manifest holds a
reference to the producing operation's output field (ORD-1) in place of a value, and the test is
made by the probe (OP-5) once the output exists. A thing that lies inside a thing another operation
moves is named relative to that operation's output: the look reads it where it is, and the probe
reads it where the move's record says it went.

Test on fakes: on a clean sunrise fixture the look's read log holds no read of a path or an id that
only a planned operation would make, and each dependent operation in the manifest holds a reference
and no value; when the producing operation is done, the dependent's probe reads the produced thing,
and a fixture in which that thing is then not in the dependent's before-state stops at that probe;
on a sunset fixture the operations on files inside a folder to be moved are planned from their
present paths and probed at the moved path.

**RUN-7. What planning decides for each candidate.**

| Planning outcome | When | What follows |
|---|---|---|
| `in` | build, create, keep: the place is free. change, move: the thing is in the row's before-state. check, owner kinds, adopt: their needs can be met (ORD-2) | the operation is in the manifest |
| `already so` | change and move only: the thing is in the row's after-state before the run has done anything | no operation; the preview lists it (FORM-2); for its way back see EV-4 and EV-5 |
| `not applicable` | a flag; the project type; a layer the project does not have; a capability the adapter did not declare, where the row names no other treatment; KEEP-2; ORD-2; EV-7 | no operation; the preview gives the reason |
| planning stop | the place is taken by a thing this run's journal does not show the run made; the thing is in neither state the row names; the read failed, was partial, was made as the wrong account, or ran out of time | the invocation ends before any preview and names each; nothing is approved |

Test on fakes: on a clear fixture every candidate is planned `in` and a manifest is written; each
planted condition of a never-clobber fixture (an existing folder, an existing remote, a taken name
at the host, a shortcut that shadows a program) ends the look with the condition named and no
manifest; so does each of a failed read, a partial read, a read made as the wrong account and a read
that ran out of time, each named; a provider resource that is already retired yields a preview line
and no operation.

**RUN-8. The manifest is the plan, and the preview is the manifest.** A manifest holds: the inputs;
the accounts, capabilities and machine locations the look read; the phases (ORD-4); every operation
with everything its row states (ROW-1), its planning outcome and the tracked state read; and every
`already so` and `not applicable` line. Every value in it is marked as one of two things: a literal
the look read, or a reference to an output's field (RUN-6). The preview is rendered from the
manifest and from nothing else. A manifest never changes once it has its go.

Test on fakes: the preview rendered twice from the manifest file, with every fake removed, is
byte-equal both times and equal to the one the owner was shown; a manifest from which any one entry
this rule lists is removed fails its validation, and no preview is rendered from it.

**RUN-9. The go is bound to the manifest.** The owner's go is recorded with the manifest's hash.
With no go on record for the manifest in force, no effect is applied. An invocation refuses a
manifest whose bytes no longer give the recorded hash, and never applies an operation the manifest
does not hold.

Test on fakes: a manifest altered after the go is refused before any operation; an operation
injected outside the manifest is refused; with no go on record no effect call is made; with a go on
record for an unaltered manifest the operations it holds run.

**RUN-10. Every later invocation needs his word again.** After the first, an invocation applies an
effect only on the owner's word to go on, given in answer to a status form of this run, and only if
(a) the journal has not grown since that form was rendered, the form's position being the count of
journal records it was rendered from, and (b) the accounts, capabilities and machine locations read
now are those the manifest holds. With no such word, or failing (a), the invocation renders the
status form and ends with no effect. Failing (b), it says a re-plan is needed (RUN-11) and ends with
no effect. His word that a waiting step is done (OP-9) is a word to go on.

Test on fakes: a resume that carries no form position, or a stale one, records no effect call and
renders the status form; a resume with the current position goes on; a resume under a different
account, with a capability changed, or with a machine location changed, each ends asking for a
re-plan with no effect call.

**RUN-11. A changed plan is a new plan, in the same run.** When the manifest in force cannot be
finished as approved (a stop that only a different plan resolves, an input the owner changes, a
thing he names for adoption, a create to be planned again under OP-7, or RUN-10 (b)), going on takes
a re-plan: a full look, a new manifest, a new preview and a new go. The journal continues. The new
manifest carries each operation the journal holds a final status for (ORD-1), with that status, as
EV-3 has it, and plans the rest afresh, the journal read first. The superseded manifest is kept.

Test on fakes: after a stop the owner drops a layer; the re-plan's preview shows the finished
operations as finished and the dropped layer's operations as `not applicable`, and no finished
operation's effect call is recorded a second time; the superseded manifest is still in the run
directory, byte-equal; a create left outstanding before the re-plan is still outstanding in the new
plan unless OP-7 resolves it.

**RUN-12. How an invocation and a run end.** An invocation runs operations (ORD-5) until none can
run or a rule says stop, then ends in exactly one of five ways, and each ending renders a status
form from the manifest and the journal.

| Ending | When | The run is then |
|---|---|---|
| `complete` | every operation is final (ORD-1) and none is `left` or `held` | ended |
| `ended with exceptions` | every operation is final and at least one is `left` or `held` | ended; each exception is listed with its reason |
| `waiting` | nothing can run and at least one operation waits on the owner | open; each waiting step is listed with its exact step and its mode; the locks are released |
| `stopped` | a rule of this frame says stop; or nothing can run, nothing waits on the owner, and an operation is not final | open; the form names the reason kind, the operation where the stop is in one, what the owner can check, and the ways on: resume, re-plan, close, and for a retirement, restore over what is finished (EV-7) |
| `closed` | RUN-13 | ended |

Test on fakes: the kill sweep's reference run ends `complete`; a fixture with an owner step ends
`waiting` with the step listed and no lock held; a planted stop inside an operation ends `stopped`
with that operation named; a stop that belongs to no operation (RUN-4, a planning stop of RUN-7)
ends `stopped` or before any preview with each cause named; a fixture with a `left` step ends
`ended with exceptions` with it listed; a closed run ends `closed`; no ending other than these five
is ever recorded.

**RUN-13. The owner can close a run.** On his word an open run is recorded `closed`. A closed run
never resumes. Closing changes nothing outside the run directory and undoes nothing; the form lists
what was done.

Test on fakes: a close on a stopped run, given his word, records one journal record and no effect
call; a close summons that does not carry his word records nothing and leaves the run open; a later
resume of the closed run is refused.

### 3.2 The journal

**LOG-1. Written ahead, durable, chained.** A journal record is appended, flushed, and synced
together with its directory before the step it describes begins; a record of an outcome is synced
before any later operation starts. Every record carries the hash of the record before it. On read, a
cut-off last record is discarded and its operation is treated as if that record had never been
written; a break in the chain anywhere else stops the invocation. The journal's records are of these
kinds and no other: the run's opening under its keys (RUN-3); a go and each later word; an
operation's start, step, answer, completion and status records; a check's attempt (OP-8); an owner
operation's waiting record and his answer; an invocation's ending; the run's ending.

Test on fakes: on a fake file system that loses every write not yet synced at a kill, a kill at
every write boundary leaves, for every effect call the fakes recorded, that operation's start record
in the journal; the journal reads back with at most its last record dropped, and the operation that
record belonged to is probed under OP-5 as if it were absent; a record of a kind this rule does not
list stops the invocation.

**LOG-2. The start record holds everything that is needed later.** Before an operation's effect the
journal holds its start record: the thing's identity and tracked state as just read; the after-state
the effect is to leave, computed beforehand and never read back; and every input a reverse would
need, each as a protected record (SEC-6) where it is content: the before-image and the after-image
of a span, the lines on each side of it, the whole definition of a thing to be cancelled, the state
a provider reported. For an effect built in staging, a step record with the staged object's identity
and, for a file, its fingerprint, is durable before the publish. For a create, the id in the
provider's answer is written, as an answer record, before anything else is done with it. A
completion record adds only what was observed.

Test on fakes: killed immediately after any effect call, every input the row's reverse names is
readable from the run directory alone, without reading the changed thing; the after-state in the
start record is the one computed before the call, so a fake that leaves a different state yields a
failed after-check and an unchanged start record; for a staged effect the step record precedes the
publish call in the fakes' sequence.

**LOG-3. The run removes only what is its own.** The only objects a run may remove are ones it made
inside its run directory or a staging folder: the private password file, a staged object that was
never published, an emptied staging folder. A swap (OP-3, C3) replaces a file's object and is not a
removal, because the before-image is on record first (LOG-2).

Test on fakes: across the whole kill sweep, every removal the fixture file system records lies under
the run directory or a staging folder that the journal recorded; the password file and each
unpublished staged object are in fact gone after the next invocation; and for every swap the
before-image's record precedes the swap call in the fakes' sequence.

### 3.3 Operations

**OP-1. One operation, one effect.** An operation of a kind that has an effect (OP-2) makes exactly
one change outside the run directory and staging, by one call that happens whole or not at all. A
command that would do more than one thing is run with the rest turned off; where the rest cannot be
turned off, the tool does not run it. A change made of several effects is several operations, each
with its own records.

Test on fakes: in the reference run, for every operation of a kind that has an effect the fake's
record shows exactly one state-changing call between that operation's start record and its
completion record; in every other run of the kill sweep, at most one.

**OP-2. The nine kinds.** A lane writes operations of these kinds and of no other.

| Kind | What it is | Its one effect | Built by (OP-3) | May declare a way back |
|---|---|---|---|---|
| check | reads and decides | none | none | no |
| build | makes a new file or folder where there is nothing, complete on arrival | the publish of a staged object | C1 | no |
| create | makes a new thing at a provider | one create request | C2 | no |
| change | takes an identified existing thing from a recorded before-state to a computed after-state, in place | one swap, one compare-and-swap, one refusing call, or one read-then-ask | C3, C4, C5, C6 | yes |
| move | puts an identified existing thing at another place | one rename | C7 | yes |
| keep | makes a checked copy of a named scope at a place with no clock | the publish of the staged copy | C1 | no |
| owner step | the owner acts; the tool shows the exact step | none by the tool | none | yes, as an owner step |
| owner answer | the owner says; the tool records | none | none | no |
| adopt | binds an output to a thing the owner named | none | none | no |

Test on fakes: a manifest that holds one well-formed operation of each of the nine kinds builds; a
manifest that holds an operation of any other kind, or of a kind with a construction its line in
this table does not allow, is refused when it is built.

**OP-3. How an effect is built.** Every effect is conditional on its whole before-state by its
construction, one of the seven below. The whole before-state is everything the row's before-test
names, on the effect's target or on anything else; a condition the construction does not enforce at
the instant of change is a window. An effect that cannot be built by one of the seven is not an
operation the tool performs. The last column is decided by RISK-1 and RISK-2.

| Id | Construction | What it enforces at the instant of change | Window that remains | Open to the tool today |
|---|---|---|---|---|
| C1 | publish from staging: the staged object (OP-4) is put at its place by a rename that fails if anything is there, an empty folder included, and never through a symbolic link | nothing is at the place; the object is the one the run built | none, under RUN-4's assumption | yes |
| C2 | a provider's create whose answer carries the new thing's id; where the row says the name must be free, a create the provider itself refuses on a taken name | the provider's own uniqueness | none at the provider | yes |
| C3 | swap: under the file's own lock, a new file is built in staging and put in the old file's place only if the old file's hash is the one in the start record; at the swap the new file takes the old file's permissions | the whole file is as recorded | a writer that ignores the lock, between the hash check and the swap | yes, under RK2 |
| C4 | compare-and-swap enforced by the store: the request names every value that must hold now, on the thing changed and on any related thing the store checks in the same request, each of which may be "none" (a local branch or tag updated only from its recorded value; a remote branch pushed only if the remote holds the value named), and the store refuses otherwise | every named value | none | yes |
| C5 | a refusing call: a call that the tool or the provider, by its own document cited in the row, refuses when the before-state does not hold; the row lists each condition the refusal covers | each listed condition | none, as far as the cited refusal goes; a condition of the before-test that is not listed is a window | yes |
| C6 | read, then ask: the state is read, then a request is sent that would also succeed if the state were already so | the state as of the read | the same change made by another between the read and the request | only for the four rows RK3 names |
| C7 | exclusive move of an identified thing: its identity is read; it is renamed by a rename that fails if anything is at the target; the identity at the target is read again, and a difference stops the run with both places named and no completion recorded | nothing is at the target | the thing at the source replaced by another between the first read and the rename | yes, under RK4 |

Test on fakes: for each construction, and for each condition its row's before-test names in turn, a
competing change is planted by the fake between the probe and the effect call. C1, C2, C4, C5: the
call fails and nothing is overwritten or taken over. C3, C6, C7: the outcome is the one the named
risk states (for C7, the run stops with both places named and no completion recorded), and the
journal marks the operation as carried under that risk. A C5 row whose listed conditions do not
cover its whole before-test fails the manifest build under RISK-2.

**OP-4. Staging.** A staged object is built in a private, owner-only folder the run made, inside the
run directory, on the same volume as the object's place; where the place is on another volume the
look stops and names the place. Building never touches the place. Every file a build makes in
staging is owner-only from its first byte. What permissions an object has once it is at its place is
its construction's and SEC-7's to say.

Test on fakes: killed at any point of a build, the place is either empty or holds the complete
object, never a partial one; every file the fake builder made in staging was owner-only at each
moment the fixture file system recorded it, also where the builder asked for wider permissions; a
place on another volume ends the look with the place named.

**OP-5. The probe.** Immediately before an operation of a kind that has an effect runs, the tool
reads the journal for it, then the world, and gives exactly one of six answers. In both halves of
the table the after-state is asked before the before-state, so a state that passes both is
`already so`, or `landed` where there is a start record. A probe only reads. No answer is inferred
from the passing of time. Checks, owner kinds and adopts are not probed this way: OP-8, OP-9 and
OP-10 say how each is decided. (For an operation with a final record, see EV-3.)

| The journal holds, for this operation | The world shows | Answer |
|---|---|---|
| nothing | the after-test holds | `already so` |
| nothing | each thing the operation names is in its expected state (EV-3) and the before-test holds | `ready` |
| a start record and no final record | the start record's after-state, on the same thing | `landed` |
| a start record and no final record | the start record's before-state, on the same thing | `not landed` |
| either | none of the above | `foreign` |
| either | the read failed, was partial, was made as the wrong account, or ran out of time | `unreadable` |

What "the same thing" means is decided by the construction, and by nothing else:

| Construction | It is the same thing when |
|---|---|
| C1 | the object at the place has the staged identity in the step record; an object there with any other identity is `foreign`, and an empty place is the before-state |
| C2 | the id read is the id in the answer record; with no answer record the create is outstanding whatever is read (OP-7) |
| C3 | it is the file at the recorded path. The object's own identity is not asked here, because a swap and an editor both replace it; whether the object in place is the staged one is asked by OP-6 |
| C4 | it is the same named branch or tag of the same repository |
| C5, C6 | it has the provider id, or is the named thing of this machine, that the start record holds |
| C7 | the object at the target has the identity read at the source into the start record, and the source holds nothing; any other pairing is `foreign` |

Test on fakes: for each kind that has an effect, fixtures for the six answers each yield that answer
and no state-changing call; a fixture with no record in which both tests hold yields `already so`,
and one with a start record in which both states hold yields `landed`; for a swap, a file replaced
by another actor with the after-content yields `landed`, and one with any other content `foreign`;
for a build, an object with another identity at the place yields `foreign`.

**OP-6. What the tool does with each answer.** Owner kinds follow OP-9 and adopt follows OP-10. On
what ground a completion record may be written is EV-1's to say; this table says only when.

| Answer | build, keep | create | change | move |
|---|---|---|---|---|
| `ready` | start record; build in staging; step record; publish; after-check; completion | start record; send; then by the answer, below | start record; effect; after-check; completion | start record; rename; after-check; completion |
| `already so` | stop: something is at the place | stop: something has the name | record `already so`; go on | record `already so`; go on |
| `not landed` | remove the staged object if there is one; start again | does not arise: outstanding (OP-7) | a new start record; the effect again | a new start record; the rename again |
| `landed` | the after-check, then completion on EV-1 (b); if the after-check fails, stop | the after-check by the recorded id, then completion on EV-1 (c); if it fails, stop | a swap whose file in place has the staged identity on record: the after-check, then completion on EV-1 (b). Any other: record `not proven`; go on | record `not proven`; go on |
| `foreign`, `unreadable` | stop | stop | stop | stop |

A create's answer: a definite success is written as the answer record (LOG-2) and the create is then
`landed`; a definite refusal that the row names as an alternative result is recorded `refused` with
its kind (ORD-3); any other definite refusal stops; an indefinite answer (none, a timeout, a
`malformed` result, a killed child) leaves the create outstanding (OP-7). For every other kind, an
effect call that fails, or an after-check that does not show the after-state, stops the run with no
completion recorded, and the next probe reads the world again.

Test on fakes: in the kill sweep, a kill at every boundary of every operation of every fake,
followed by a resume, ends in the cell this table names for it; and in every run the fakes' sequence
and the journal show, for each operation, the start record before the effect call, the step record
before a publish, the after-check's read after the effect call, and the completion record after the
after-check.

**OP-7. A create whose answer was lost.** A create with a start record and no recorded answer is
outstanding, whatever the world shows, and the run stops. It stays in the journal, is read by every
later look for the project key, and is resolved only in one of three ways.

| Way | It requires | Then |
|---|---|---|
| the provider answers for that request | a read that the provider documents as the status of that very request, cited in the row | "made, with this id": the after-check and completion. "made nothing and will make nothing": the create may be planned again, by a re-plan |
| the provider guarantees a second send cannot make a second thing | a name the provider keeps unique in the account and scope the run is bound to, or the provider's own idempotency key, cited in the row | the create may be planned again, by a re-plan whose preview says an earlier send got no answer. If the name is then found taken, the thing there is not proven the run's: a planning stop, which he clears by hand |
| the owner drops the layer | nothing | by a re-plan the layer is left out. He cannot name an existing thing to stand in its place (OP-10). The tool never sends that create again |

An empty listing, the owner's word that nothing is there, and the passing of time resolve nothing.

Test on fakes: a fake that makes the thing and loses the answer, then lists nothing for a while: the
resume stops as outstanding and sends nothing, and no later invocation under the same manifest sends
it; a re-plan offers the create again only for a fake that declares a guarantee or whose status read
for that request answers "made nothing and will make nothing", and sends it only after that
re-plan's own go; a status read that answers "made, with this id" completes the create on EV-1 (c)
with no second send; dropping the layer yields a manifest without it and no send; across every such
fixture the fake's state never holds two things.

**OP-8. Checks.** A check has no before-state and no after-state. Each time it is made is an
attempt, recorded on its own with the invocation that made it, the tracked state of the subject it
read, and its answer: `passed`, `failed` or `unavailable`. No attempt is ever erased or rewritten.
`unavailable` is given only when the check needs a capability the adapter did not declare in the
look; the preview says so beforehand and the summary says so afterwards. A `failed` attempt stops
the run, and the check is attempted again on resume. A need on a check (ORD-1) is met only by its
latest attempt, and only if that attempt read the subject in the tracked state it has now and, where
the operation that needs it has an effect, was made in that operation's own invocation. Where the
latest attempt does not meet a need of the next operation that could otherwise run, the check is
attempted again first. A further attempt is not a reopening: EV-3 concerns operations with an effect
and owner kinds. A subject that cannot be read is a stop.

Test on fakes: a failing kit line stops the run; a harness without the canary capability yields a
preview line, an `unavailable` attempt, and a run that can end `complete` with the line in its
summary; a scan that passed in one invocation is attempted again in the next before the push, and
the journal then holds both attempts; a scan that passed on one commit does not let the push run
when an approved operation has since made another commit the head: it is attempted again on the new
head, and the push's start record names the same commit as the attempt that let it run.

**OP-9. Owner operations.** The script never performs the owner's step for him. Each owner operation
has one mode, fixed in the manifest and shown in the preview.

| Mode | Complete when | His saying "done" | Final status |
|---|---|---|---|
| step, read back | the tool's own read shows the after-state, whether or not he has said anything | asks for the read to be made again | `done by owner, read back` |
| step, on his word | his typed "done" is recorded; used only where the tool has no read | completes it | `done by owner, on his word` |
| answer | his typed answer, one of the answers the row allows, is recorded with its value | does not arise | `answered` |

Until it is complete the operation is `waiting`. Every waiting step in read-back mode is read again
at the start of each invocation. The step shown to him is built from safe content (SEC-1) by a fresh
read each time, never from an earlier form and never by repeating an effect. Where he must read
content before he answers, the row gives a review file (SEC-6). An answer that is not on the row's
list is refused and the operation stays `waiting`. The value of a recorded answer is what needs and
conditions name (ORD-1, ORD-3); an answer has no other consequence. In any mode his answer "leave
it" records the operation `left`.

Test on fakes: a step in read-back mode completes on the read alone and never on his word alone; a
step on his word completes on the word and is listed as not checked; an answer the row does not list
is refused and nothing is recorded as `answered`; a waiting step shown again after the provider's
state changed shows what the fresh read gave and not the earlier form's text; "leave it" ends the
wait as `left`; no fake records a call that performs an owner's step.

**OP-10. Adopt.** Adoption is offered for one output and for no other: the local project folder (the
owner's ruling, A6). An adopt is in a manifest only because the owner's own input names that folder
by its path. The tool never puts one into a plan from what it found. The preview shows the thing's
identity and the tracked state read. When it runs, the tool reads the thing again and requires it to
be as the manifest recorded, or it stops; the record `adopted` binds the output's fields to it and
changes nothing. What an adoption releases is in ORD-1 and EV-2.

Test on fakes: a thing found at a planned place without the owner's input ends in a planning stop
and never in an adopt; with his input naming a local folder the manifest holds an adopt and the
dependents with state needs run; a folder changed between the look and the adopt stops the run with
no `adopted` record; a row that offers adoption for any other output fails the manifest build.

**OP-11. Every command that can change a repository is declared.** The manifest lists, under its
operation, each command the run will execute that can change a repository or a remote, including any
that a builder program runs inside staging. A builder program is run with its repository writes
turned off where it can be; where it cannot, its writes are listed line by line; a builder whose
repository writes cannot be listed beforehand is not run.

Test on fakes: in the reference run the fake git's record of state-changing calls, the fake
scaffolder's included, equals the manifest's list, in order; in a run that is stopped, killed or
resumed it is that list's beginning, then after the resume the rest, with a call repeated only where
OP-6 says "again"; a fake scaffolder whose repository writes are neither turned off nor listed fails
the manifest build and is never started.

### 3.4 Proof

**EV-1. What proves the run did it.** The run may say it did a thing on one of three grounds, and on
nothing else. (a) Its completion record: written in the same invocation as the effect call, after
that call returned a definite success (SEC-4) and after the after-check read the after-state. (b)
The built object: the object in place has the identity the journal recorded for an object the run
built in staging, the record made before the publish, and the after-check passes now. (c) The
recorded answer, for a create and for nothing else: an answer record, written in the invocation that
received it, holds the id from the provider's own answer to the run's own request, which is either
the create call's definite success or the provider's documented status of that very request (OP-7);
and the after-check by that id, under the expected account and scope, passes now. On grounds (b) and
(c) a later invocation may write the completion record. A start record with a matching state, a
marker written beforehand, equal content, a name, a time, a listing, a read made afterwards without
one of these three grounds, and the owner's statement are not grounds.

Test on fakes: for each kind, the by-hand fixture (a start record on disk, the run killed before the
effect, the fake then put in the after-state by another actor) never yields `done`; the
killed-after-publish fixture yields `done` on resume only where the object in place has the staged
identity on record; a create killed after its answer record yields `done` on resume by a read of
that id, and a create killed before any answer record never does, whatever a listing shows; an
effect whose call returned an indefinite answer never yields `done` in that invocation, even where
the after-state is then read.

**EV-2. Three facts, kept apart.** For every output the journal keeps three separate facts, and none
is ever taken for another.

| Fact | Established by | It allows |
|---|---|---|
| the state holds | any read that shows it | needs at the state level (ORD-1) |
| the thing is bound: the run knows which thing is the project's for this output | for a thing that existed before the run: the look's resolution, confirmed by the owner. For a thing the run was to make: `done` or `adopted`, and nothing else | references to the output's fields (RUN-6) |
| the run is its author | `done` only (EV-1) | needs at the made level (ORD-1); a way back (EV-4) |

Test on fakes: an empty remote repository of the approved name, planted before the create runs,
stops the run with nothing pushed to it and nothing linked to it; a row whose need is at the made
level never runs on `already so`, `not proven` or `adopted`; and no operation that refers to a field
of an output the run was to make runs before that output's provider is `done` or `adopted`, whatever
state a read shows.

**EV-3. Completion is history; the present is checked per thing.** An operation of a kind that has
an effect, an owner operation and an adopt, once it has a final record, is never probed or read
again and is never reopened, by a resume or by a re-plan. (A check is the one kind attempted again:
OP-8.) For each thing, the journal keeps the tracked state every operation of the run left it in or
read it in. When an operation is about to run, each thing it names must be in the last tracked state
the journal holds for it or, where the journal holds none, in the state the manifest recorded at the
look. A difference is `foreign`, unless it is the operation's own target standing in a state OP-5
names. So an approved later change to a thing becomes that thing's expected state, and no other
change passes.

Test on fakes: a commit, then approved edits to tracked files, then a kill before the next commit:
the resume makes exactly one more commit, applies no operation twice, and the fakes' read log holds
no probe of any operation that had a final record; the same sequence with one unapproved edit
planted before the resume stops and names the file; and an operation one of whose named things,
other than its target, was changed by another actor stops and names that thing.

**EV-4. When a way back may be recorded.** A way back is recorded for an operation when all four
hold, and only then: its row declares one (ROW-1); the operation is `done`; every input the reverse
needs was on disk before the effect (LOG-2); and the reverse is itself an operation this frame
allows. In every other case the record says "no way back" with one reason from this list: the row
declares none; found already so; not proven; an input is missing; done by the owner.

Test on fakes: every `done` operation whose row declares a way back and whose inputs are on record
has that way back recorded; for each final status other than `done`, and for a `done` operation with
an input removed, the record's way-back field is "none" with the matching reason.

**EV-5. What a restore offers.** A restore builds its manifest from the retiring run's journal. It
offers the reverse of each operation that has a way back on record (EV-4) and of no other, with two
additions the owner ruled (A6): for an operation that ended `not proven`, it lists it and offers the
reverse only if the owner asks for that line in the restore's look, and every form then says it runs
on his word and was not proven the run's; for an owner step that ended `done by owner`, in either
mode, it offers the reverse as an owner step in the same mode. It may copy from a keep (KEEP-4).
Everything it does not offer it lists, with the reason EV-4 recorded. Every reverse is an ordinary
operation under every rule of this frame. A reverse that needs the output of a reverse that is not
offered is planned by ORD-2.

Test on fakes: from a sunset journal holding one operation of each final status, the restore's
manifest holds the reverse of the `done` operation with a way back, the `not proven` reverse only
with the owner's answer and with its form line saying so, the owner step's reverse as an owner step,
and no other; a reverse whose thing is not in the last tracked state the retiring journal holds
stops under EV-3; a reverse that needs the output of one not offered is settled as ORD-2's test line
says.

**EV-6. Putting text back.** A span the retiring run replaced is put back only when its recorded
after-image occurs in the file exactly once; the recorded before-image then takes its place and
nothing else in the file moves. A span the retiring run removed is put back by the placement its row
declares. `in place`: the recorded lines on each side are found next to each other exactly once and,
for a file the row marks as ordered (one where a line's meaning depends on what stands before it),
everything before that point is as recorded. `at the end`: allowed only for a file the row marks as
unordered, where the span is absent and nothing else already does what it does. Where the declared
placement cannot be met the probe answers `foreign`; the form names the file, the place and the
protected records, and shows no text of the file or of a record.

Test on fakes: a status line the owner edited after the sunset stops the restore with nothing
changed and no file text in any output; so does an after-image that occurs twice, and so do recorded
neighbours that occur next to each other twice; a removed line between two different lines returns
between them, and with a line inserted above it in an ordered file the restore stops; a row that
declares `at the end` for a file it marks as ordered fails the manifest build; an alias line returns
at the end of the shortcut file only when its name is free.

**EV-7. A restore is a run.** It has its own look, manifest, preview, go, journal and phases
(ORD-4), and never runs the retiring run's order backwards. It reads the journal of the project
key's latest retiring run, whatever that run's ending; if that run is open, the restore's go closes
it. Where a protected record or a keep that the restore needs is missing or fails its fingerprint,
the operations that need it are planned `not applicable` with that reason, and the rest are still
offered.

Test on fakes: a restore over a sunset that stopped after its barrier reverses exactly the
operations that are `done` with a way back, and that sunset run is `closed` once the restore has its
go; with two retiring runs on record for the key, the later one is the one read; a missing protected
record, and a keep whose fingerprint no longer matches, each take only their dependents out of the
offer, with the reason in the preview.

### 3.5 Order

**ORD-1. Outputs, needs, and what meets them.** Every operation provides one named output. An
operation's needs are written against output names, each at one of four levels (state, made, passed,
answered), and it runs only when every need is met. There are thirteen final statuses, the rows of
this table. Each cell says what a provider that ended in that status is to a need at that level:
`meets`; `stop`; `his` (the owner's own answer or his own "leave it" is why); or `branch` (a branch
of the plan that was not taken).

| The provider's final status | state | made | passed | answered |
|---|---|---|---|---|
| `done` | meets | meets | stop | stop |
| `already so`, at planning or in the run | meets | stop | stop | stop |
| `not proven` | meets | stop | stop | stop |
| `adopted` | meets | stop | stop | stop |
| `passed` | stop | stop | meets, as OP-8 limits it | stop |
| `unavailable` | stop | stop | meets where the need is marked as accepting it; otherwise stop | stop |
| `refused` | branch | branch | branch | branch |
| `done by owner, read back` | meets | stop | stop | stop |
| `done by owner, on his word` | meets where the need is marked as accepting his word; otherwise stop | stop | stop | stop |
| `answered` | stop | stop | stop | meets with a value the need names; his with any other value |
| `left` | his | his | his | his |
| `not needed` | branch | branch | branch | branch |
| `held` | his | his | his | his |

A need can no longer be met when every operation that provides its output is final and none of them
meets it. What follows is then decided by those providers' cells, in this order. If any of them is
`stop`, the run stops (RUN-12): the form gives the reason kind "need unmet" and names the operation
that has the need, the need, and the provider's status; that operation gets no status, so the run
stays open and a re-plan can settle it (RUN-11, ORD-2). This is the owner's ruling for `not proven`
(A11) and the governing rule's for every other `stop` cell (GOV-1). Otherwise, if any of them is
`his`, the operation that has the need is recorded `held`, with the need and the provider's status
as its reason, and the run goes on (the owner's rulings, A6 at O14, and A11). `held` is recorded in
this case and in no other, which is why a `held` provider is itself `his`. Otherwise every one of
them is `branch`, and the run stops in the same way as for a `stop` cell (GOV-1).

Test on fakes: a table-driven test over all fifty-two pairs of final status and level, each with one
provider, asserts its cell: for `meets`, the operation runs; for `stop` and for `branch`, the run
ends `stopped` with the reason kind "need unmet" and the operation, the need and the status named,
no `held` record is written, the run is open, and no last record is published; for `his`, the
operation is `held` with its reason, the rest of the run goes on, and the run ends
`ended with exceptions`. With two providers: `not proven` beside `left` stops; `refused` beside
`left` is `held`; `refused` beside `not needed` stops. After such a stop, a re-plan that settles the
need as ORD-2 says, and has its own go, lets the run go on.

**ORD-2. A need on an output that nothing provides.** When a manifest is built, a need that names an
output no operation in it provides is settled then, by the treatment the row declares for that need:
`then not applicable` (the needing operation is left out as well, and so on down the line) or
`then not needed` (the need is dropped). A need at the state level is instead met outright where the
look read that state as already holding. A need at the made level on an output that only an adopt
provides counts as unprovided. So does, at a re-plan, a need that the journal shows can no longer be
met (ORD-1): it is settled by the same declared treatment, and the new preview names the operation
left out or the need dropped, and the status that caused it. A need with no declared treatment, a
need left pointing at nothing, or a circle of needs, fails the build and names the row. Nothing
about the shape of the plan is settled after the go.

Test on fakes: over a lane's rows, every combination of project type and flag that the lane's brief
lists as one the owner may ask for builds a manifest in which no need points at nothing; a planted
row with a need that has no treatment, and a planted circle of needs, each fail at build with the
row named; none of these fails during a run; and a re-plan after a "need unmet" stop builds a
manifest in which that need is settled by its row's treatment and the preview says so.

**ORD-3. Conditions and alternatives.** An operation may carry one condition, of one of three kinds.
On a planning fact: settled when the manifest is built, and the operation is `in` or
`not applicable`. On an alternative result of an earlier operation of the same manifest: settled
when that operation ends; true, the operation can run; false, it is recorded `not needed`. On the
value of an earlier owner answer of the same manifest (OP-9): settled when the answer is recorded,
in the same way. An alternative result is a definite refusal the provider module declares (SEC-4),
named in the row; the operation that receives it is final as `refused`, and each alternative result
a row names is the condition of at least one operation. Several operations may provide the same
output as alternatives: the output is established by the one of them that reaches a status meeting a
need, once each of the others is final as `refused` or `not needed`. Where all of them are final and
none established it, ORD-1 says what becomes of what needs it. Two alternatives that could run at
the same time fail the build.

Test on fakes: with a provision that answers `terms`, it is recorded `refused`, the terms step and
the second provision run, the output is established by the second, and the dependents run once,
after it; with a provision that succeeds, the terms step and the second provision are recorded
`not needed` and the dependents run once; in neither does a dependent run before the output is
established. An operation whose planning condition is false is `not applicable` in the manifest. An
operation conditioned on one value of an answer runs on that value and is `not needed` on another.
Two alternatives with no condition between them fail the build.

**ORD-4. Phases.** A manifest's operations are in ordered phases, each operation in one. No
operation of a phase starts until every operation of every earlier phase is final and that phase's
gate, where this frame gives it one (KEEP-3), holds. Inside a phase only needs order the work, so an
operation that waits on the owner holds back its dependents and the next phase, and nothing else.
For a retirement the phases are these, in this order (the owner's rulings, A2 and A4): keeping,
which holds every keep and every other operation that preserves and none that retires; retiring on
this machine; retiring at the providers; the last record (KEEP-5). For a restore, an operation that
starts something running again (a schedule, a routine, a launch agent's load) is in a later phase
than every operation that puts back what it runs on, and the last record is last. The rest of a
restore's phases, and a sunrise's, are the lane's to declare. A manifest whose phases break this
rule, or that holds an operation in a phase this rule denies it, fails its build.

Test on fakes: with an owner step waiting in one phase, every operation of that phase that does not
need it still runs and no operation of a later phase starts; in a retirement no provider retirement
call is recorded before the last machine retirement is final; a retirement manifest that declares
the provider phase before the machine phase, or puts a retiring operation in the keeping phase,
fails its build; a restore manifest that loads a schedule in the phase that moves its repository
back fails its build.

**ORD-5. One at a time, in a fixed order.** An invocation runs one operation at a time: the first,
in the manifest's order, whose phase is open, whose condition is true and whose needs are met; a
check that OP-8 says must be attempted again for that operation is attempted first. When there is
none, it ends (RUN-12).

Test on fakes: in the reference run every operation of the manifest is run, and two runs of one
fixture record the same sequence of calls; no two effect calls of one run overlap in the fakes'
records.

### 3.6 Keeping, retiring, and a run's last record

**KEEP-1. A keep is whole, or it is not a keep.** A keep copies a named scope of a thing to a place
with no clock. What "whole" means is read from the same consistent state that is copied: the
inventory is taken inside the same snapshot or hold as the copy, the copy is compared with it, and
the completion record holds the inventory, the copy's size and fingerprint, and the identity of the
source as read inside that same state. Where the whole scope cannot be read or established, the keep
fails and the run stops; where the look can already see that, it is a planning stop. No partial copy
is offered as a keep, by a flag or by a go.

Test on fakes: a schema that appears between the look and the copy is in the copy, or the keep
fails; a table that cannot be read ends the look with its name; no input yields a manifest that
holds a partial keep; and with a fake source that changes right after the snapshot, the completion
record's inventory, source identity, size and fingerprint each equal what the fake held at the
snapshot, and the copy at its place matches them.

**KEEP-2. A retirement is tied to its keeps before the go.** An operation that retires a thing
(moves it away, removes it, cancels it, pauses, archives or idles it) names the keeps it requires.
It is planned `in` only if the look read the same identity from both sides: from the source each
required keep will copy, and from the thing the operation would retire. Where that cannot be read,
the keep stays in the plan, the retirement is `not applicable`, the preview says what will not be
retired and the step the owner can take himself, and the rest of the run goes on. That is the one
outcome for a copy that cannot be tied to what it would cover. When the retirement runs, its probe
requires the identity in each required keep's completion record to equal the identity of its target
as read then.

Test on fakes: a database that the provider's side cannot identify yields a manifest with the keep
and without the idle, the preview line, a run that completes, and no idle call; a dump taken from a
different database than the one to be idled stops before the idle; a target whose identity changes
between the go and the retirement stops before the retirement's call; with one identity on both
sides throughout, the idle is made.

**KEEP-3. The barrier.** No operation that retires anything starts unless, in the same invocation,
every keep in the manifest is `done` and has just been checked again in full: at its place, with the
permissions SEC-7 requires, of the recorded size and fingerprint, and passing the content checks its
row declares. A failure stops the run with nothing further retired.

Test on fakes: with every keep intact the retirements run, in the first invocation and after a
resume; a dump cut short between two invocations stops the resume at the barrier with every fake
still live and every path where it was; the same cut made after some retirements are done stops the
resume before the next one.

**KEEP-4. Keeps stay.** No operation of any run changes, moves or removes a keep.

Test on fakes: a planted row whose effect would write to, move or remove a keep's place fails the
manifest build; after a sunset, a restore and a second sunset, every keep of the first exists at its
place and equals its recorded fingerprint.

**KEEP-5. A run's last record.** Where a lane has a run write its own record among the project's
things (a sunset's tombstone, a restore's entry), that operation is alone in the last phase, runs
only when every other operation of the manifest is final, is rendered from the journal alone, and is
published once. Until that publish, a run that is `waiting`, `stopped` or `closed` has written none.
Between the publish and its completion record the entry is at its place and not yet confirmed: the
publish and the journal are two writes, and the frame does not pretend they are one. On resume the
operation is probed like any other (OP-5): a `landed` entry is confirmed by its after-check and
completed (OP-6); an entry that cannot be confirmed leaves the run `stopped`, the form saying that
the entry is at its place and unconfirmed, and the ways on are resume and close. No run rewrites or
removes an entry once it is published, its own included. The project's record is a history: each
run adds its own entry and never rewrites, refreshes or removes an entry an earlier run wrote, and
an earlier run's entry at the place is not a collision.

Test on fakes: with the database step waiting, no tombstone exists anywhere; once the step is read
back the tombstone is written once and shows the final state, and with every fake but the file
system removed before it is rendered it is the same, byte for byte; a kill between the publish and
the completion record is followed by a resume that confirms the one entry and ends the run
`complete`, with no second publish; an entry damaged after its publish leaves the run `stopped`
with the entry untouched and named as unconfirmed; a second sunset after a restore adds an entry and
leaves the first byte-equal.

### 3.7 Secrets

**SEC-1. Three classes of content.** Content is protected until a line of this table makes it safe.
Only safe content may appear in the journal, a manifest, a form, the CLI's output or an error;
secret and protected content rest only where SEC-7 allows and travel only by SEC-2.

| Class | What it is |
|---|---|
| secret | a provider's token; a database password; a value of an env file; a key or certificate file; the data in a dump; any value a declaration seals as a secret (SEC-4) |
| protected | content the run read from the owner's files or from a tool and has not made safe: a schedule's command, a launch agent's file, a memory note, the before-image or after-image of a span, the present text of a file, a sealed field (SEC-4) |
| safe | text the tool itself wrote from safe content; a field SEC-4 promotes; content of a file that a validator the row declares has passed, where that validator promotes only as SEC-4 allows; the owner's own words given in this run and validated (SEC-9) |

Test on fakes: a canary planted in each secret source and each protected source, and each value a
fake issues during the run in a sealed field, appear, by the scan of SEC-11, in no journal record,
manifest, form, output or error; and the same run's forms hold the safe fields FORM-2 requires, so
an implementation that shows nothing fails.

**SEC-2. Channels.** The hosting token is read in-process by one function, from the environment
variable, else from the hosting tool's own credentials file opened read-only (the owner's ruling,
A2). It is used only in requests the frame itself makes to the provider's fixed host, over TLS,
following no redirect and logging no request, and is then dropped. The database password travels to
the dump tool in a private password file: built in the run directory, owner-only from its first
byte, named to the tool by a path in its environment (SEC-3), and removed when the tool ends and at
the start of the next invocation if a kill left it. The database address's host, port, database name
and user name are safe content. The git host's tool keeps its own token; the frame never reads it.
A protected record that a tool or the harness adapter needs (a routine's definition to recreate) is
handed over only through a protected input (SEC-3).

Test on fakes: the fake host records that the authorization header arrived with the right hash and
that no redirect was followed; with the environment variable absent and a fixture credentials file
present, the same header arrives, and the fixture file system shows that file opened read-only and
left byte-equal; the fake dump tool records the password file's path in its environment and finds
the file owner-only, and the file is gone after the call and after a kill and resume.

**SEC-3. The child process.** Every child is started by one runner, and only as this table says. A
call to a capability of the harness adapter is declared and bounded the same way, and its answer is
parsed by SEC-4.

| Aspect | Contract |
|---|---|
| command | an argument list built from the row's declared template, filled with validated inputs and output fields; never a shell line |
| environment | built from nothing. It holds the base names `HOME`, `PATH`, `USER`, `LOGNAME`, `LANG` and `LC_ALL` (the last two set to one fixed locale) and `TMPDIR` (set to a private folder in the run directory), and the names the provider module registered for that command, each of one class: fixed (a safe literal); passed (copied from the session, only for a name registered with its reason, never for a name the module lists as carrying a credential); private path (the path of an owner-only file the frame made). Nothing else of the session reaches a child |
| protected input | a slot the declaration names, with the type of protected record it accepts (SEC-6). The frame fills it only with the path of an owner-only file it made from that record, passed in the environment name or the argument position the slot declares. The content is never an argument, never an environment value and never in the CLI's output |
| refusals | the runner refuses: a command with no declaration; an argument on the tool's registered list of debug, verbose and trace flags; any argument or environment value that holds an entry of the secret register in any form SEC-12 names |
| files it makes | a file-creation mask that gives every new file to the owner only; the working directory the row declares |
| input and output | standard input empty; both output streams captured in memory up to a fixed size and handed only to the parser of SEC-4; output over that size is discarded and the result is `malformed` |
| lifetime | its own process group; a time limit from the declaration; at the limit, or when the invocation is ending, the runner ends the group it started, every descendant in it included, and nothing else |

Test on fakes: the fake records its arguments and the names of its environment, and the names equal
the base list plus the registered names; a session debug variable and a session token variable are
absent; a command with no declaration, a trace flag, and a register entry planted in an argument
whole, by component, percent-encoded and in base64 are each refused before the start; a protected
input reaches the fake as a path to an owner-only file and its content is in no argument or
environment value; a file the fake creates is owner-only; a fake that hangs after starting a child
of its own is ended at its limit with that child, and the result is `timeout`.

**SEC-4. What a provider's result may carry.** A provider module declares, for each command, its
result fields. Each field has: a name; the place in the tool's structured answer it is read from;
one type from the list below; for each result the command can give, whether the field is required
in it; and one disposition: promoted, sealed, or sealed as a secret. The frame reads a field only
from its declared place, never by searching the tool's text, and keeps nothing that is not declared.

| Type | Validator | May be promoted to safe |
|---|---|---|
| exit | an integer | yes |
| kind | one of `not-found`, `auth`, `conflict`, `terms`, `timeout`, `malformed`, `other` | yes |
| state | one of the words the module registers for that command | yes |
| count | a non-negative integer | yes |
| flag | true or false | yes |
| time | a timestamp in one registered form | yes |
| id | the provider's identifier: an alphabet and a length limit the module registers | only with a declared meaning from the list below, or where the value equals safe content the run already holds |
| name | a key name or a resource name: letters, digits and the punctuation the module registers, with a length limit | the same |
| hash | a fingerprint in a registered form | the same |
| address | a link whose host and path match a pattern the module registers for that command, with no user part, no fragment, and no query parameter but those the declaration lists, each with its own type and disposition | only if its path and every parameter in it may be promoted; otherwise the whole address is sealed |

The meanings that allow an open value (an id, a name, a hash, a part of an address) to be promoted
are these and no other, each cited in the declaration from the provider's own document: the
identifier or the name of a resource, an account or a team, as the provider shows it in its own
listings; the name of a key; the address of a commit; a page of the provider's own site that carries
no parameter. A value whose declared meaning is a credential, a code, a signed or one-time link, or
a connection address is sealed as a secret: it enters the secret register (SEC-12) on receipt,
before any other field of that result is read. An open value with no declared meaning is sealed. A
sealed value is written straight to a protected record (SEC-6), is referred to only by reference,
and is never promoted afterwards.

An undeclared field is dropped. A declared field that fails its validator, a required field that is
missing, an address with a fragment or with a parameter the declaration does not list, or a promoted
value that holds an entry of the secret register, turns the whole result into kind `malformed` with
nothing promoted. The module also declares, per command, which results are definite: the success
that proves the effect happened, and the kinds that prove it did not; every other result is
indefinite.

Test on fakes: a fake that adds a field, mistypes one, omits a required one, or echoes a register
entry inside one: the first is dropped, the others yield `malformed`, and no value from such a
result is in the journal; a fake that returns a declared address carrying a freshly issued value in
an unlisted parameter or in a fragment yields `malformed`, and one that carries it in a listed,
sealed parameter yields a protected record and a form line with a file path, and in both the issued
value is in no journal record, form or output; an id declared with no meaning is sealed and never
shown; an omitted optional field does not make the result `malformed`; a result the declaration
does not list as definite is treated as indefinite by OP-6, and a declared definite success as
definite.

**SEC-5. Nothing a tool prints is kept or shown** (the owner's ruling, A4). What the owner or the
executor sees of a failure is the operation, the kind, and the command with its declared arguments,
so that he can run it himself and read the tool's words in his own terminal. An exception is
reported as its type and the operation; its message is never printed.

Test on fakes: a fake that fails echoing a canary whole, in part, encoded, and split across reads
leaves it in no output, form or file, and the stop's form holds the operation, the kind and the
command with its declared arguments; a planted exception whose message holds the canary is reported
by type and operation alone.

**SEC-6. A protected record is named, never shown.** It is a file in the run directory's protected
folder. The journal, a manifest and a form refer to it only by: an id the run assigns, never derived
from the content; its type (before-image, after-image, definition, line, values, copy, sealed
field); a label the tool wrote from safe content; and a fingerprint keyed with a random value made
for the run and kept only in that folder. Where the owner must have the content (to recreate a
schedule by hand, to judge a merge before he answers, to open a sealed link), the form names the
file's path and says he opens it himself; a file made for him to read before an answer is a review
file, kept in the same folder on the same terms.

Test on fakes: for a schedule whose saved command holds a canary, on a harness with no capability to
recreate it, the owner's step names a file path and a label, and the canary is in no form or output;
the same holds for a review file whose content holds a canary; the journal's fingerprint of a record
is not the plain hash of its content, and two runs give two different fingerprints for the same
content.

**SEC-7. Where a secret or a protected record may rest.** These places and no other, each reached by
the construction this table gives and never through a symbolic link. A place found with wider
permissions than this table gives is a failure.

| Place | What rests there | How it gets there, and its permissions |
|---|---|---|
| the frame's own memory | the hosting token; values on their way to a file; the secret register (SEC-12) | read in-process; dropped after use; written nowhere |
| the private password file | the database password | a new file built by the frame (SEC-2); owner-only; removed after use |
| the protected folder of the run directory | protected records, review files, the fingerprint key | new files built by the frame; owner-only; kept with the run |
| staging | a secret-bearing object while it is built | OP-4; until it is published or removed |
| the pulled env file in the working tree | env values | a new file: staged and published by C1; owner-only; ignored by git, proven before every commit (SEC-10) |
| the sunset folder beside the archived repository | the dump, the saved hosting env values, the memory copy | new files: staged and published by C1 as keeps; owner-only, in an owner-only folder outside every working tree (the owner's ruling, A2) |
| the same sunset folder | a launch agent's file moved there | the file itself, moved by C7; it keeps the permissions it had, inside the owner-only folder |
| the place a thing was taken from, on a restore | a launch agent's file moved back | the file itself, moved by C7 to its original place and no other; it keeps the permissions it had |
| the same | a span put back into its file (EV-6) | a swap, C3, of the file it was taken from and no other; the file keeps the permissions it has, never wider |
| the same | the working memory store copied back from its keep | new files: staged and published by C1 at the original place, which must be empty of anything; with the permissions recorded at the retirement, never wider |
| the same | a routine recreated through the adapter | a protected input (SEC-3) |
| the provider | the token in the authorization header; the password, to the database server | the authorized transmissions of SEC-2 |

What a tool writes into its own folders is not on this list: it is risk RK1 (RISK-1).

Test on fakes: clean runs of sunrise, sunset and restore produce each artifact this table names (the
env file, the dump, the saved env values, the memory copy, the protected records, the moved launch
agent's file, the span put back, the store copied back), and the canary is found only at these
places, each reached by the construction and holding the permissions the table gives; a link planted
at any of them fails the operation with nothing written through it.

**SEC-8. A tool writes a new secret-bearing output only into staging.** The frame checks it there
and publishes it (C1). A tool that cannot be pointed at a staging path, or that has a secret-writing
side effect of its own which cannot be turned off, is not run for that purpose.

Test on fakes: the fake hosting tool's pull writes into a staging path, and the env file appears in
the working tree owner-only and complete; a fake that can only write in place is never started; nor
is a fake whose declaration names a second secret-writing side effect with no way to turn it off.

**SEC-9. Inputs are validated before they are stored.** An input that holds a secret (an address
with a password in it, a description that holds an entry of the secret register) is refused at the
start and is stored nowhere.

Test on fakes: a summons with a password inside an address, and one whose description holds a
register entry, each end refused, and the canary is in no file of the fixture home; a summons with
neither is accepted and its inputs are in the manifest.

**SEC-10. Nothing is committed or pushed unscanned.** Before every commit a check scans, by content,
exactly what will be committed and proves the ignore rule; before a push a check scans every commit
to be pushed. A hit stops the run, names the file and shows nothing.

Test on fakes: a canary in the content about to be committed stops the run before the commit, also
where the working-tree file has since been cleaned; a canary in a working-tree file that is not part
of what will be committed does not; a canary in an earlier commit stops the run before the push; in
each stop the output names the file and holds no canary; with no canary the commit and the push are
made.

**SEC-11. How the secret rules are tested.** A marked canary, built at run time, is planted in every
source SEC-1 names, and every value a fake issues during a run in a sealed field is recorded by the
fake for the scan. The scan covers every file under the fixture home and the fixture working tree,
both output streams, every argument and environment that every fake recorded for itself and for
anything it started, at any depth, and every git object. It looks for the canary and for each issued
value whole, for each of its components, and for the percent-encoded and base64 forms of both. One
found outside a place of SEC-7, or at one with wider permissions than SEC-7 gives, fails. The fake
host records only that an authorization header arrived and whether its hash is the expected token's;
it never stores the header.

Test on fakes: the scan is itself proven: a canary planted in each scanned place, in each form, is
found, including in the recorded arguments of a fake's own child; a canary at a place of SEC-7 with
wider permissions is reported; an issued value planted in a form is found.

**SEC-12. The secret register.** There is one register for an invocation, held in memory and written
nowhere. A value enters it at one of four moments and at no other: when the frame reads a secret
from a channel of SEC-2, at the read and before any runner or parser use; when a result field sealed
as a secret is received (SEC-4), before any other field of that result is read; when an input is
checked (SEC-9); and when the run's fingerprint key is made or read (SEC-6). An entry holds the
value whole, each component its source declares (for a connection address: the password, and the
user and password pair), and the percent-encoded and base64 forms of each. The runner (SEC-3), the
result parser (SEC-4), the input check (SEC-9) and every write to the journal, a manifest, a form,
the CLI's output or an error consult it. A later invocation starts with an empty register and fills
it from the channels again before any runner use. A secret the frame never reads into memory (a
value inside a file a tool wrote into staging) is not in the register; SEC-11's scan is what checks
that it reached no output.

Test on fakes: a value a fake issues in a field sealed as a secret, and then asks for back in an
argument of a later command or returns in a promoted field of a later result, is refused by the
runner or turns that result `malformed`; the register's content is in no file of the fixture home;
a resumed invocation refuses a planted channel secret in an argument before its first child starts.

### 3.8 Forms

**FORM-1. Where a form's text comes from.** A form is a file in the run directory, named in the
CLI's output and shown by the adapter. Its text comes from four sources only: v1's fixed text for
that form, the lines of FORM-2, text the tool wrote from validated inputs and fields, and the
owner's own words.

Test on fakes: with a canary in every protected source and in every tool's output, each form of each
run is rendered and holds no canary, and holds each line FORM-2 requires for the statuses that
occurred, with the parts FORM-2 names; a form template that reads a file's text directly fails its
build test.

**FORM-2. Every status has a line, in every form that lists operations.** A preview, a status form,
a summary and a last record can each show every line below, and a lane's list of form changes
includes them. A status that occurs in a run and has no line in a form that lists operations fails
that form's build.

| For | The line says |
|---|---|
| `done` | what was done |
| `already so` | found already so; a restore will not reverse it |
| `not proven` | started by this run and not proven finished by it; a restore will ask before reversing it |
| `adopted` | taken as the project's on the owner's input, with its identity |
| `waiting` | the exact step, its mode, and how the tool will know it is done |
| `done by owner` | done by him, and whether a read checked it |
| `left` | left, by his word |
| `held` | not run, and the operation it waited on |
| `refused`, `not needed` | which branch was taken |
| `not applicable` | the reason: a flag, the project type, a layer the project lacks, not available on this harness, or cannot be tied to its copy, with the step he can take himself |
| `unavailable` | the check could not be made on this harness |
| an outstanding create | a create was sent and no answer came; what he can check; the ways on |
| a stop | the operation, the kind, the command he can run, the ways on |
| a protected record | its label and the path of its file |

Test on fakes: a run driven through every status in this table renders every form with the matching
line, and each line holds the parts its row names (for `waiting` the step and the mode, for
`done by owner` whether a read checked it, for `held` the operation waited on, for `not applicable`
the reason, for a protected record the label and the path); a form template that lacks one of these
lines, or renders one without a part its row names, fails its build test.

**FORM-3. A restore has forms of its own.** A restore has a preview, a status form, a summary, and
its entry in the project's record (KEEP-5). They are forms under FORM-1 and FORM-2, and are not
changes to a v1 form.

Test on fakes: a restore run renders each of the four; its preview lists exactly the reverses EV-5
offers and, with its reason, each operation not offered; each of the four holds the FORM-2 line of
every status that occurred in that restore.

### 3.9 What a row states

**ROW-1. A row states all of this, or the manifest is not built from it.**

| A row states | Used by |
|---|---|
| its id, kind and phase | OP-2, ORD-4 |
| the thing it acts on: its role, how its identity is read, and its tracked state; or the output field it refers to | RUN-6, OP-5, EV-3 |
| its planning test | RUN-6, RUN-7 |
| its before-test and its after-test | OP-5 |
| its construction; for C2 and C5 the document cited, and for C5 each condition the refusal covers; for C3, C6 and C7, and for a shortcut's add or put-back, each accepted risk it is carried under | OP-3, RISK-1, RISK-2 |
| its one effect as a declared command: the argument template, the registered environment names, any protected input, the time limit; each result field with its place, type, meaning, disposition and whether it is required; the definite results; the alternative results | OP-1, SEC-3, SEC-4, ORD-3 |
| each command that can change a repository | OP-11 |
| its after-check | OP-6, EV-1 |
| the output it provides and that output's fields; each need, with its level, the answer value it names where the level is answered, and its treatment when nothing provides it; its condition | ORD-1, ORD-2, ORD-3 |
| for a create: how a lost answer can be resolved, with the provider's document, or "by dropping the layer only" | OP-7 |
| its way back, or "none" with the reason; for a span, its placement and whether the file is ordered | EV-4, EV-6 |
| for an owner kind: its mode, the safe content its step is built from, the answers it allows, any review file | OP-9, SEC-6 |
| for the local project folder, the one output that may be adopted: how the owner names it | OP-10 |
| for a keep: its scope, how the inventory and the copy share one state, and its content checks. For a retirement: the keeps it requires | KEEP-1, KEEP-2, KEEP-3 |
| the class of every content it reads, stores or shows; any validator that makes content safe; each resting place it uses | SEC-1, SEC-7 |
| its lines in each form | FORM-2 |

Test on fakes: for each kind, a complete and well-formed row builds; the same row with each required
entry removed in turn fails the manifest build and names the entry; and a row whose entry is present
but not allowed (a construction OP-2 does not give its kind, an accepted risk that does not cover
its construction, a level ORD-1 does not have, a meaning SEC-4 does not list) fails the same way.

**ROW-2. A step becomes the owner's only by his word.** Where a lane finds a tool that cannot be
split into single effects (OP-1), whose repository writes cannot be listed (OP-11), or that cannot
be pointed at staging (SEC-8), the lane reports it before its rows are read, and the step is put to
the owner before it becomes his (the owner's ruling, A6). A row that stands an owner step in for
such an effect cites his ruling on it.

Test on fakes: a manifest built from a row that stands an owner step in for an effect the tool will
not run fails its build and names the row where no ruling is cited, and builds where one is.

**ROW-3. A lane's rows are admitted only with its checklist answered.** The contract and the lane's
brief hold a checklist of what the owner has ruled that this frame does not itself carry. A lane's
rows are read, and a manifest is built from them, only where every item of that checklist is
answered by a row, by a form line, or by a stated reason that it is not that lane's. What the
checklist holds is the contract's and the brief's to say, not this frame's.

Test on fakes: over a lane's rows and its checklist file, an admission test passes where every item
names the row, the form line or the reason that answers it, and fails naming the item where one is
unanswered or names a row that does not exist.

## Part 4. The risk that is left

**RISK-1. The accepted risks stand as the catalog's Part 6 states them.** The owner accepted five
risks and one assumption (the contract's section 18, A4 and A6): RK1; RK2, which by his word covers
every swap, C3; RK3, for the four rows it names; RK4, for a move, C7; RK5, for a shortcut's name
being free, in the add and in the put-back; and the run directory's assumption (RUN-4). Their
wording is in the catalog's Part 6 and is not restated here. This frame removes none of them and
accepts none itself. An operation carried under RK2, RK3, RK4 or RK5 is marked so in the journal,
once for each of those risks it is carried under.

Test on fakes: every operation built by C3, C6 or C7 carries the mark of its risk; a shortcut's add
and its put-back carry RK5's mark beside RK2's; each mark is recorded exactly once for its operation
and its risk, also after a kill and a resume; no other operation carries a mark.

**RISK-2. A window nobody accepted is not the tool's to take.** A row whose effect has a window that
no accepted risk names is written as an owner step (OP-9), and a manifest that holds it as a tool's
effect fails its build. Two such windows were put to the owner and ruled no (A6), and stay his
steps: C6 outside the four rows RK3 names; and a schedule table that can only be read and then
replaced through its own tool, which no construction of OP-3 covers. A before-test condition on
something the effect does not change, which the row's construction does not enforce, stays closed in
every case but the one RK5 names.

Test on fakes: a manifest that holds, as a tool's effect, a read-then-ask on a row RK3 does not
name, an edit of a schedule table, or a row whose before-test names something its effect does not
change and whose construction does not enforce it, other than a shortcut's name, fails its build and
names the row; the same condition enforced in the same request by a C4, or covered by a C5's cited
refusal, builds; and a manifest of rows whose every window is named by an accepted risk builds.

## Part 5. Worked examples (illustration only; the rules are the source)

One draft row of the catalog's Part 4 for each of the nine kinds, walked through a kill at each
boundary and the resume that follows. The rows are drafts: a lane may write them differently. Each
line gives what is on disk and in the world, the probe's answer, the move, and the rules applied.

### Example 1. check: the scan before the push (draft row SR14)

It needs the kit check `passed`. Its subject is every commit to be pushed.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the attempt's record | no record of the check | attempt 1 is made | OP-8 |
| after attempt 1, `passed`, on commit c2 | attempt 1 on record, made by the killed invocation | attempt 1 stays in the journal. The push has an effect and needs a pass made in its own invocation, so attempt 2 is made on c2; then the push is probed | OP-8, ORD-5, SEC-10 |
| variant: attempt 1 passed on c2, and an approved operation has since made c3 the head | the subject's tracked state is c3 | attempt 1 no longer meets the push's need: a new attempt is made on c3, and the push names c3 | OP-8, EV-3 |
| variant: a pass is on record, and a commit that no operation of the run made is now the branch's head | the branch is not in its last tracked state | `foreign`: stop, naming the repository | EV-3 |
| variant: the scan finds a hit | an attempt `failed` | stop, the file named, nothing shown; attempted again on resume | OP-8, SEC-10, RUN-12 |

### Example 2. build: the project folder from zero (draft rows SR01 and SR02 as one operation)

The folder is built in staging: the scaffolder runs inside it with its repository writes turned off
or listed (OP-11), then the folder is published to the developer root by C1.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the start record | nothing | `ready`: the operation runs from the start | OP-5, OP-6 |
| after the start record, while the scaffolder runs | a partial folder in staging; the place empty; no step record | `not landed`: the staged folder is removed and built again | OP-6, LOG-3 |
| after the step record, before the publish | a complete folder in staging with its identity on record; the place empty | `not landed`: removed and built again | OP-6 |
| after the publish, before the completion record | staging empty; the folder at the place has the identity on record | `landed`: the after-check, then completion on ground (b): `done` | OP-6, EV-1 |
| variant: killed before the publish, and the owner then makes a folder of that name by hand | the place holds a folder with another identity | `foreign`: stop, naming what is there | OP-5, EV-2 |
| after the completion record | `done` | not probed; the next operation runs | EV-3 |

At no boundary is a half-made project folder at the place.

### Example 3. create: the remote repository (draft row SR08)

Built by C2 with a name the provider keeps unique. Its output is needed at the made level by the
push.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the start record | nothing | `ready`: the create is sent | OP-6 |
| after the start record, before the send, or after the send with no answer | a start record and no answer record; the repository may or may not exist | outstanding: stop. The row cites the provider's unique names, so a re-plan may plan the create again, its preview saying an earlier send got no answer. If the name is then taken: a planning stop, and the repository there is not proven the run's | OP-7, RUN-11 |
| after the answer record, before the completion record | the id from the call's own answer in the journal | `landed`: the after-check by that id, under the expected account, then completion on ground (c): `done` | LOG-2, OP-5, OP-6, EV-1 |
| variant: the answer record is there and the read by that id finds nothing | the answer and the world disagree | `foreign`: stop | OP-5 |
| after the completion record | `done` | not probed | EV-3 |
| variant: the answer is `conflict` | a definite refusal, nothing made by this call | stop: something has the name | OP-6 |

### Example 4. change: remove the shortcut lines (draft row T11)

Built by C3 under RK2. The start record holds the file's hash, each line and the lines on each side
of it as protected records, and the after-image. For a swap the thing is the file at its path
(OP-5); which object is there is asked only to decide the ground of proof.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the start record | the file as the look read it | `ready` | OP-5 |
| after the start record, before the swap (with or without the staged file) | the lines still in the file | `not landed`: any staged file is removed; a new start record; the swap again | OP-6 |
| after the swap, before the completion record | the after-state holds; the file in place has the staged identity on record | `landed`: the after-check, then completion on ground (b), with its way back recorded | OP-5, OP-6, EV-1, EV-4 |
| variant: killed before the swap, and the owner then deletes the lines by hand, his editor replacing the file | the after-state holds; the file in place is neither the old object nor the staged one | `landed`, because the thing is the file at that path: `not proven`; the run goes on; no way back is recorded, and a restore asks before reversing it | OP-5, OP-6, EV-4, EV-5 |
| variant: another actor replaces the file with other content | neither state of the start record | `foreign`: stop | OP-5 |
| variant: a program that ignores the lock rewrites the file after the probe | the hash differs at the swap | the swap is not made: stop. On resume the probe reads the file again | OP-3, RISK-1 |

### Example 5. move: the repository to the archive folder (draft row T12)

Built by C7 under RK4 (RISK-1). RK4 covers the instant between the read and the rename; it does not
give a way back to a move whose completion record was lost.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the start record | the repository at its path, with the head the look recorded | `ready` | OP-5 |
| after the start record, before the rename | the same | `not landed`: a new start record; the rename again | OP-6 |
| after the rename, before the completion record | the source absent; the target holds the identity on record | `landed`: `not proven`; the run goes on, later operations reading the new path from this record; a restore asks before reversing it | OP-6, EV-2, EV-5 |
| variant: killed before the rename, and the owner then moves the folder by hand | exactly the same as the line above | the same: `not proven`. The run does not claim the move | EV-1 |
| after the completion record | `done`, with its way back recorded | not probed | EV-3, EV-4 |
| variant: another folder is put at the source between the identity read and the rename | the target holds a folder with another identity | the read after the rename differs: stop with both places named and no completion recorded; on resume the probe answers `foreign` | OP-3, RISK-1 |
| variant: both paths hold a folder, or neither does, or the target holds another identity | neither state of the row | `foreign`: stop, naming both places | OP-5 |

### Example 6. keep: the database dump (draft row T03)

In the look, KEEP-1 found the whole scope readable and KEEP-2 read one identity from both sides. The
dump tool writes into staging; the inventory is taken in the same snapshot; the tool's own lister
reads the archive to its end.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the start record | nothing | `ready` | OP-5 |
| while the dump tool runs | a partial archive in staging; the password file present | the password file is removed at the start of the invocation; `not landed`: the staged archive is removed and the dump is made again | SEC-2, OP-6 |
| after the step record, before the publish | a complete archive in staging | `not landed`: removed and made again | OP-6 |
| after the publish, before the completion record | the archive in the sunset folder with the identity on record | `landed`: the after-check in full, then completion on ground (b) | OP-6, EV-1 |
| after completion, the run stopped before the barrier, and the archive later cut short | `done` on record; the file smaller than recorded | the barrier's re-check fails: stop, with nothing retired | KEEP-3 |
| variant: a schema the role cannot read appears in the snapshot | the inventory and the copy cannot be shown whole | the keep fails: stop before the barrier, the project still live | KEEP-1 |

### Example 7. owner step: idle the database (draft row T22), in read-back mode

| Moment | On disk and in the world | What happens | Rules |
|---|---|---|---|
| a kill before the `waiting` record | no record | read again; the `waiting` record and the step are written | OP-9 |
| waiting; he pauses it in the dashboard and says done | `waiting` on record; the provider reports paused | the read shows the after-state: `done by owner, read back`; the last record can now be written | OP-9, KEEP-5 |
| waiting; he says done, and the provider still reports live | `waiting` | it stays `waiting`; the form says what the read showed | OP-9 |
| waiting; he says nothing; a later invocation's read shows paused | `waiting` | completed by the read | OP-9 |
| waiting; he answers "leave it" | `waiting` | `left`; the run ends with exceptions and its last record lists the step as left | OP-9, RUN-12, KEEP-5 |
| while it waits | every other operation of its phase that does not need it has run | the tombstone has not been published | ORD-4, KEEP-5 |
| a kill after the tombstone is published and before its completion record | the entry at its place, with the staged identity on record | `landed`: confirmed by its after-check and completed; no second entry | KEEP-5, OP-6 |

A restore offers the reverse as an owner step in the same mode (EV-5).

### Example 8. owner answer: approve a merged kit file (the draft's SR03a)

The merged candidate is built in staging and a review file is made; the form names its path. The
row allows two answers, "use it" and "keep the old file". The swap that follows has a need at
the answered level that names "use it".

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the `waiting` record | no record | the candidate and the review file are built again; `waiting` | OP-9, SEC-6 |
| after the `waiting` record | the review file in the protected folder | still `waiting`; the form names the file again | OP-9 |
| after his answer "use it" is on record | `answered`, with that value | not asked again; the swap's need is met and the swap is probed | EV-3, ORD-1 |
| variant: he answers "keep the old file" | `answered`, with that value | the swap's need names another value and can no longer be met: the swap is `held` with that reason and does not run; the rest of the run goes on and it ends with exceptions | OP-9, ORD-1, RUN-12 |
| variant: he types something else | nothing recorded as `answered` | refused; still `waiting` | OP-9 |
| his answer record cut off | the last record discarded | asked again | LOG-1 |
| variant: he answers "leave it" | `left` | the swap is `held`, with that as its reason; the run ends with exceptions | ORD-1, RUN-12 |

### Example 9. adopt: the project folder under `--promote` (draft row SR01, its second case)

The owner's input names the folder. The look reads its identity and tracked state; the manifest
holds an adopt for the output "project folder" in place of the build, and the preview shows the
identity.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the `adopted` record | the folder as the manifest recorded it | read again; the record is written; nothing in the folder changes | OP-10 |
| after the `adopted` record | `adopted` | not read again; operations with state needs on the folder run | EV-3, ORD-1 |
| variant: the folder changed between the go and the adopt | not as the manifest recorded | stop | OP-10 |
| variant: no input named the folder, and the look finds it at the planned place | a thing at the place | a planning stop; no adopt is planned | RUN-7, OP-10 |
