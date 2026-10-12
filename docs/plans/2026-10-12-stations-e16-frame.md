# E16 frame: the executor's rules, the proof a run may claim, and how a secret travels

Written 2026-10-12 by a new author, on the owner's word (the lane contract
`docs/plans/2026-10-11-stations-e16.md`, section 18, A5), from the outside reviewer's three design
reads. **This document is the single source for the frame.** It replaces Parts 1 to 3 of the
operation catalog (`docs/plans/2026-10-12-stations-e16-operations.md`): the rules X1 to X13, the
evidence classes E1 to E4 and the secret rules K1 to K8 are withdrawn. The owner's rulings (the
contract's sections 5 and 18) stand above this document. This document stands above every lane's
rows: a row that cannot be written under these rules is not written, and the lane stops and asks.
**Status: not yet read by the outside reviewer. No slice has the owner's go.**

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
recorded after the stop.

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

## Part 3. The rules

### 3.1 Runs, the look, the plan and the owner's word

**RUN-1. Every invocation starts the same way.** In this order: the gate (the vault and machine
checks); the locks (RUN-2); the run directory opened, or made for a new run (RUN-4); the rest of the
look (RUN-5). Nothing comes before the gate, the cue included. A failed gate ends the invocation
with nothing created and no lock taken.

Test on fakes: with no vault, with a stub vault, and with a vault inside a synced folder, the
invocation ends refused; the fixture home is byte-equal to before; no lock file exists; the cue fake
recorded no call.

**RUN-2. One lock per project key.** The project key is the project's name folded: lowercased, with
every character that is not a letter or a digit removed. An invocation takes the lock of the key of
the name it was summoned with before it reads any thing of the project, and the lock of the key of
every other name form the look resolves for the project on any layer before the manifest is built,
in sorted order. A lock is of the kind the system releases when its holder dies, and is never broken
by age. An invocation that meets a held lock ends at once, names the run that holds it, and reads
nothing more. A file that the runs of other projects also change has a lock of its own, held only
around the one change (OP-3, C3).

Test on fakes: of two invocations summoned with two spellings of one name (a different case, a
hyphen against an underscore), the second ends on the lock with no probe call recorded; after the
first is killed a third takes the lock; two runs of different projects that change one shared file
both land their change.

**RUN-3. One open run per project key.** A run is open from its first go (RUN-9) until it ends
`complete`, `ended with exceptions` or `closed` (RUN-12). While a key has an open run, a summons for
that key may only resume it (RUN-10), re-plan it (RUN-11) or close it (RUN-13); any other summons is
refused and names the open run. The one exception is in EV-7.

Test on fakes: with a sunrise left `waiting`, a sunset summons for the same key is refused with the
open run named and with no read past the lock recorded.

**RUN-4. The run directory, and the one assumption.** The run directory is a private folder in the
owner's home directory, outside every repository, one folder per run, owner-only, and kept after the
run ends (the owner's ruling, A2). It holds the inputs, every manifest, the journal, the protected
records, the forms and staging. Every proof in this frame assumes that nothing but the run changes a
run directory or a staging folder. The frame checks what it can: at the start of every invocation
the run directory and everything in it must be owner-only and the journal's chain (LOG-1) must hold,
or the invocation stops.

Test on fakes: a run-directory file given wider permissions between two invocations stops the second
before it reads any thing of the project; a byte changed in the middle of the journal does the same.

**RUN-5. The look only reads.** Before the owner's word an invocation changes nothing outside its
run directory. The look reads: the tools on the path and each provider's identity, which is the
account every remote operation will act as; what the harness adapter declares it can do (its
capabilities); the journals of the project key's earlier runs; the planning facts of RUN-6; and the
owner's answers that shape the plan. An answer taken in the look is an input of the run, validated
(SEC-9) and recorded in the manifest. A look that lacks an answer it needs ends the invocation with
the questions listed and nothing approved. Nothing a look read is carried to a later invocation
except through the manifest.

Test on fakes: with every fake recording its calls, a look that reaches its preview records only
read calls and leaves the fixture home and every fake's state byte-equal; a look with an unanswered
question ends with the question listed and no manifest written.

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
and no value; on a sunset fixture the operations on files inside a folder to be moved are planned
from their present paths and probed at the moved path.

**RUN-7. What planning decides for each candidate.**

| Planning outcome | When | What follows |
|---|---|---|
| `in` | build, create, keep: the place is free. change, move: the thing is in the row's before-state. check, owner kinds, adopt: their needs can be met (ORD-2) | the operation is in the manifest |
| `already so` | change and move only: the thing is in the row's after-state before the run has done anything | no operation; the preview lists it (FORM-2); for its way back see EV-4 and EV-5 |
| `not applicable` | a flag; the project type; a layer the project does not have; a capability the adapter did not declare, where the row names no other treatment; KEEP-2; ORD-2 | no operation; the preview gives the reason |
| planning stop | the place is taken by a thing this run's journal does not show the run made; the thing is in neither state the row names; the read failed, was partial, was made as the wrong account, or ran out of time | the invocation ends before any preview and names each; nothing is approved |

Test on fakes: each planted condition of a never-clobber fixture (an existing folder, an existing
remote, a taken name at the host, a shortcut that shadows a program) ends the look with the
condition named and no manifest; a provider resource that is already retired yields a preview line
and no operation.

**RUN-8. The manifest is the plan, and the preview is the manifest.** A manifest holds: the inputs;
the accounts, capabilities and machine locations the look read; the phases (ORD-4); every operation
with everything its row states (ROW-1), its planning outcome and the tracked state read; and every
`already so` and `not applicable` line. The preview is rendered from the manifest and from nothing
else. A manifest never changes once it has its go.

Test on fakes: the preview rendered twice from the manifest file, with every fake removed, is
byte-equal both times and equal to the one the owner was shown.

**RUN-9. The go is bound to the manifest.** The owner's go is recorded with the manifest's hash.
With no go on record for the manifest in force, no effect is applied. An invocation refuses a
manifest whose bytes no longer give the recorded hash, and never applies an operation the manifest
does not hold.

Test on fakes: a manifest altered after the go is refused before any operation; an operation
injected outside the manifest is refused; with no go on record no effect call is made.

**RUN-10. Every later invocation needs his word again.** After the first, an invocation applies an
effect only on the owner's word to go on, given in answer to a status form of this run, and only if
(a) the journal has not grown since that form was rendered, and (b) the accounts, capabilities and
machine locations read now are those the manifest holds. With no such word, or failing (a), the
invocation renders the status form and ends with no effect. Failing (b), it says a re-plan is needed
(RUN-11) and ends with no effect. His word that a waiting step is done (OP-9) is a word to go on.

Test on fakes: a resume that carries no form position, or a stale one, records no effect call and
renders the status form; a resume with the current position goes on; a resume under a different
account, or with a capability changed, ends asking for a re-plan.

**RUN-11. A changed plan is a new plan, in the same run.** When the manifest in force cannot be
finished as approved (a stop that only a different plan resolves, an input the owner changes, a
thing he names for adoption, a create to be planned again under OP-7, or RUN-10 (b)), going on takes
a re-plan: a full look, a new manifest, a new preview and a new go. The journal continues. The new
manifest carries each operation the journal holds a final status for (ORD-1), with that status, and
plans the rest afresh, the journal read first. It never reopens a final operation. The superseded
manifest is kept.

Test on fakes: after a stop the owner drops a layer; the re-plan's preview shows the finished
operations as finished and the dropped layer's operations as `not applicable`, and no finished
operation's effect call is recorded a second time.

**RUN-12. How an invocation and a run end.** An invocation runs operations (ORD-5) until none can
run or a rule says stop, then ends in exactly one of five ways, and each ending renders a status
form from the manifest and the journal.

| Ending | When | The run is then |
|---|---|---|
| `complete` | every operation is final (ORD-1) and none is `left` or `held` | ended |
| `ended with exceptions` | every operation is final and at least one is `left` or `held` | ended; each exception is listed |
| `waiting` | nothing can run and at least one operation waits on the owner | open; each waiting step is listed with its exact step and its mode; the locks are released |
| `stopped` | a rule of this frame says stop | open; the form names the operation, the reason kind, what the owner can check, and the ways on: resume, re-plan, close, and for a retirement, restore over what is finished (EV-7) |
| `closed` | RUN-13 | ended |

Test on fakes: the kill sweep's reference run ends `complete`; a fixture with an owner step ends
`waiting` with the step listed and no lock held; each planted stop ends `stopped` with exactly one
operation named; no ending other than these five is ever recorded.

**RUN-13. The owner can close a run.** On his word an open run is recorded `closed`. A closed run
never resumes. Closing changes nothing outside the run directory and undoes nothing; the form lists
what was done.

Test on fakes: a close on a stopped run records one journal line and no effect call; a later resume
of that run is refused.

### 3.2 The journal

**LOG-1. Written ahead, durable, chained.** A journal line is appended, flushed, and synced together
with its directory before the step it describes begins; a line that records an outcome is synced
before any later operation starts. Every line carries the hash of the line before it. On read, a
cut-off last line is discarded and its operation is treated as if that line had never been written;
a break in the chain anywhere else stops the invocation.

Test on fakes: killed at every write boundary, the journal reads back with at most its last line
dropped, and the operation that line belonged to is probed under OP-5 as if the line were absent.

**LOG-2. The start record holds everything that is needed later.** Before an operation's effect the
journal holds its start record: the thing's identity and tracked state as just read; the after-state
the effect is to leave, computed beforehand and never read back; and every input a reverse would
need, each as a protected record (SEC-6) where it is content: the before-image and the after-image
of a span, the lines on each side of it, the whole definition of a thing to be cancelled, the state
a provider reported. For an effect built in staging, a step record with the staged object's identity
and, for a file, its fingerprint, is durable before the publish. For a create, the id in the
provider's answer is written before anything else is done with it. A completion record adds only
what was observed.

Test on fakes: killed immediately after any effect call, every input the row's reverse names is
readable from the run directory alone, without reading the changed thing.

**LOG-3. The run removes only what is its own.** The only objects a run may remove are ones it made
inside its run directory or a staging folder: the private password file, a staged object that was
never published, an emptied staging folder. A swap (OP-3, C3) replaces a file's object and is not a
removal, because the before-image is on record first (LOG-2).

Test on fakes: across the whole kill sweep, every removal the fixture file system records lies under
the run directory or a staging folder that the journal recorded.

### 3.3 Operations

**OP-1. One operation, one effect.** An operation makes exactly one change outside the run directory
and staging, by one call that happens whole or not at all; a check, an owner kind and an adopt make
none. A command that would do more than one thing is run with the rest turned off; where the rest
cannot be turned off, the tool does not run it. A change made of several effects is several
operations, each with its own records.

Test on fakes: for every operation of every fake, the fake's record shows at most one
state-changing call between that operation's start record and its completion record.

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

Test on fakes: a manifest that holds an operation of any other kind, or of a kind with a
construction its line in this table does not allow, is refused when it is built.

**OP-3. How an effect is built.** Every effect is conditional on its whole before-state by its
construction, one of the seven below. The whole before-state is everything the row's before-test
names, on the effect's target or on anything else; a condition the construction does not enforce at
the instant of change is a window. An effect that cannot be built by one of the seven is not an
operation the tool performs. The last column is decided by RISK-1 and RISK-2.

| Id | Construction | What it enforces at the instant of change | Window that remains | Open to the tool today |
|---|---|---|---|---|
| C1 | publish from staging: the staged object is put at its place by a rename that fails if anything is there, and never through a symbolic link | nothing is at the place; the object is the one the run built | none, under RUN-4's assumption | yes |
| C2 | a provider's create whose answer carries the new thing's id; where the row says the name must be free, a create the provider itself refuses on a taken name | the provider's own uniqueness | none at the provider | yes |
| C3 | swap: under the file's own lock, a new file is built in staging and put in the old file's place only if the old file's hash is the one in the start record; the new file carries the old file's permissions | the whole file is as recorded | a writer that ignores the lock, between the hash check and the swap | yes, under RK2 |
| C4 | compare-and-swap enforced by the store: the request names the value the thing must hold now, which may be "none" (a local branch or tag updated only from its recorded value; a remote branch pushed only if the remote holds the value named), and the store refuses otherwise | the named value | none | yes |
| C5 | a refusing call: a call that the tool or the provider, by its own document cited in the row, refuses when the before-state does not hold | what the cited refusal covers; the row shows that it covers the whole before-state | none, as far as the cited refusal goes | yes |
| C6 | read, then ask: the state is read, then a request is sent that would also succeed if the state were already so | the state as of the read | the same change made by another between the read and the request | only for the four rows RK3 names |
| C7 | exclusive move of an identified thing: its identity is read; it is renamed by a rename that fails if anything is at the target; the identity at the target is read again, and a difference stops the run with both places named and no completion recorded | nothing is at the target | the thing at the source replaced by another between the first read and the rename | no |

Test on fakes: for each construction a competing change is planted by the fake between the probe and
the effect call. C1, C2, C4, C5: the call fails and nothing is overwritten or taken over. C3, C6:
the outcome is the one the named risk states, and the journal marks the operation as carried under
that risk. C7: the run stops with both places named.

**OP-4. Staging.** A staged object is built in a private, owner-only folder the run made, inside the
run directory, on the same volume as the object's place; where the place is on another volume the
look stops and names the place. Building never touches the place. Every file a build makes in
staging is owner-only from its first byte.

Test on fakes: killed at any point of a build, the place is either empty or holds the complete
object, never a partial one; a place on another volume ends the look with the place named.

**OP-5. The probe.** Immediately before an operation runs, the tool reads the journal for it, then
the world, and gives exactly one of six answers. The after-test is asked before the before-test, so
a state that passes both is `already so`. A probe only reads. No answer is inferred from the passing
of time. (For an operation with a final record, see EV-3.)

| The journal holds, for this operation | The world shows | Answer |
|---|---|---|
| nothing | the after-test holds | `already so` |
| nothing | each thing the operation names is in its expected state (EV-3) and the before-test holds | `ready` |
| a start record and no final record | the start record's before-state | `not landed` |
| a start record and no final record | the start record's after-state, with the identity on record | `landed` |
| either | none of the above | `foreign` |
| either | the read failed, was partial, was made as the wrong account, or ran out of time | `unreadable` |

Test on fakes: for each kind, fixtures for the six answers each yield that answer and no
state-changing call; a fixture in which both tests hold yields `already so`.

**OP-6. What the tool does with each answer.** Owner kinds follow OP-9 and adopt follows OP-10.

| Answer | check | build, keep | create | change | move |
|---|---|---|---|---|---|
| `ready` | read and decide (OP-8) | start record; build in staging; step record; publish; after-check; completion | start record; send; then by the answer, below | start record; effect; after-check; completion | start record; rename; after-check; completion |
| `already so` | does not arise | stop: something is at the place | stop: something has the name | record `already so`; go on | record `already so`; go on |
| `not landed` | does not arise | remove the staged object if there is one; start again | outstanding (OP-7) | a new start record; the effect again | a new start record; the rename again |
| `landed` | does not arise | the after-check, then completion on EV-1 (b); if the after-check fails, stop | if the journal holds the answer's id: the after-check by that id, then completion. Otherwise outstanding (OP-7) | a swap whose file in place has the staged identity on record: completion on EV-1 (b). Any other: record `not proven`; go on | record `not proven`; go on |
| `foreign`, `unreadable` | stop | stop | stop | stop | stop |

A create's answer: a definite success with an id leads to the after-check by that id and completion;
a definite refusal that the row names as an alternative result is recorded `refused` with its kind
(ORD-3); any other definite refusal stops; an indefinite answer (none, a timeout, a `malformed`
result, a killed child) leaves the create outstanding (OP-7). For every other kind, an effect call
that fails, or an after-check that does not show the after-state, stops the run with no completion
recorded, and the next probe reads the world again.

Test on fakes: in the kill sweep, a kill at every boundary of every operation of every fake,
followed by a resume, ends in the cell this table names for it.

**OP-7. A create whose answer was lost.** A create with a start record and no recorded answer is
outstanding, whatever the world shows, and the run stops. It stays in the journal, is read by every
later look for the project key, and is resolved only in one of three ways.

| Way | It requires | Then |
|---|---|---|
| the provider answers for that request | a read that the provider documents as the status of that very request, cited in the row | "made, with this id": the after-check and completion. "made nothing and will make nothing": the create may be planned again, by a re-plan |
| the provider guarantees a second send cannot make a second thing | a name the provider keeps unique in the account and scope the run is bound to, or the provider's own idempotency key, cited in the row | the create may be planned again, by a re-plan whose preview says an earlier send got no answer. If the name is then found taken, the thing there is not proven the run's: a planning stop |
| the owner takes it | nothing | by a re-plan he names a thing for adoption, where the row offers that (OP-10), or he drops the layer. The tool never sends that create again |

An empty listing, the owner's word that nothing is there, and the passing of time resolve nothing.

Test on fakes: a fake that makes the thing and loses the answer, then lists nothing for a while: the
resume stops as outstanding; a re-plan offers the create again only for a fake that declares a
guarantee; across every such fixture the fake's state never holds two things.

**OP-8. Checks.** A check has no before-state and no after-state. It runs when its needs are met,
reads, and answers `passed`, `failed` or `unavailable`. `unavailable` is given only when the check
needs a capability the adapter did not declare in the look; the preview says so beforehand and the
summary says so afterwards. A `failed` check stops the run and is made again on resume. A `passed`
record names the tracked state it read. An effect that needs a check requires that same state at its
own probe and a pass made in its own invocation, and the check is made again where the pass on
record is from an earlier one. A subject that cannot be read is a stop.

Test on fakes: a failing kit line stops the run; a harness without the canary capability yields a
preview line, an `unavailable` record, and a run that can end `complete` with the line in its
summary; a scan that passed in one invocation is made again in the next before the push.

**OP-9. Owner operations.** The script never performs one. Each has one mode, fixed in the manifest
and shown in the preview.

| Mode | Complete when | His saying "done" | Final status |
|---|---|---|---|
| step, read back | the tool's own read shows the after-state, whether or not he has said anything | asks for the read to be made again | `done by owner, read back` |
| step, on his word | his typed "done" is recorded; used only where the tool has no read | completes it | `done by owner, on his word` |
| answer | his typed answer, one of the answers the row allows, is recorded | does not arise | `answered` |

Until it is complete the operation is `waiting`. Every waiting step in read-back mode is read again
at the start of each invocation. The step shown to him is built from safe content (SEC-1) by a fresh
read each time, never from an earlier form and never by repeating an effect. Where he must read
content before he answers, the row gives a review file (SEC-6). In any mode his answer "leave it"
records the operation `left`.

Test on fakes: a step in read-back mode completes on the read alone and never on his word alone; a
step on his word completes on the word and is listed as not checked; "leave it" ends the wait as
`left`; no fake records a call that performs an owner step.

**OP-10. Adopt.** An adopt is in a manifest only because the owner's own input names the thing by
its identity (a path he gave, an id he gave), for an output whose row offers adoption. The tool
never puts one into a plan from what it found. The preview shows the thing's identity and the
tracked state read. When it runs, the probe requires the thing to be as the manifest recorded; the
record `adopted` binds the output's fields to it and changes nothing. What an adoption releases is
in ORD-1 and EV-2.

Test on fakes: a thing found at a planned place without the owner's input ends in a planning stop
and never in an adopt; with his input the manifest holds an adopt and the dependents with state
needs run.

**OP-11. Every command that can change a repository is declared.** The manifest lists, under its
operation, each command the run will execute that can change a repository or a remote, including any
that a builder program runs inside staging. A builder program is run with its repository writes
turned off where it can be; where it cannot, its writes are listed line by line; a builder whose
repository writes cannot be listed beforehand is not run.

Test on fakes: the fake git's record of state-changing calls, the fake scaffolder's included, equals
the manifest's list, in order.

### 3.4 Proof

**EV-1. What proves the run did it.** The run may say it did a thing on one of two grounds, and on
nothing else. (a) Its completion record: written in the same invocation as the effect call, after
that call returned a definite success and after the after-check read the after-state; for a create,
the id is the one in the call's own answer, read back under the expected account and scope. (b) The
built object: the object in place has the identity the journal recorded for an object the run built
in staging, the record made before the publish, and the after-check passes now; on this ground a
later invocation may write the completion record. A start record with a matching state, a marker
written beforehand, equal content, a name, a time, a read made afterwards, and the owner's statement
are not grounds.

Test on fakes: for each kind, the by-hand fixture (a start record on disk, the run killed before the
effect, the fake then put in the after-state by another actor) never yields `done`; the
killed-after-publish fixture yields `done` on resume only where the object in place has the staged
identity on record.

**EV-2. Three facts, kept apart.** For every output the journal keeps three separate facts, and none
is ever taken for another.

| Fact | Established by | It allows |
|---|---|---|
| the state holds | any read that shows it | needs at the state level (ORD-1) |
| the thing is bound: the run knows which thing is the project's for this output | for a thing that existed before the run: the look's resolution, confirmed by the owner. For a thing the run was to make: `done` or `adopted`, and nothing else | references to the output's fields (RUN-6) |
| the run is its author | `done` only (EV-1) | needs at the made level (ORD-1); a way back (EV-4) |

Test on fakes: an empty remote repository of the approved name, planted before the create runs,
stops the run with nothing pushed to it and nothing linked to it; a row whose need is at the made
level never runs on `already so`, `not proven` or `adopted`.

**EV-3. Completion is history; the present is checked per thing.** An operation with a final record
is never probed again, and its after-test is never asked again. For each thing, the journal keeps
the tracked state every operation of the run left it in or read it in. When an operation is about to
run, each thing it names must be in the last tracked state the journal holds for it or, where the
journal holds none, in the state the manifest recorded at the look. A difference is `foreign`,
unless it is the operation's own target standing in a state OP-5 names. So an approved later change
to a thing becomes that thing's expected state, and no other change passes.

Test on fakes: a commit, then approved edits to tracked files, then a kill before the next commit:
the resume makes exactly one more commit and applies no operation twice; the same sequence with one
unapproved edit planted before the resume stops and names the file.

**EV-4. When a way back may be recorded.** A way back is recorded for an operation only when all
four hold: its row declares one (ROW-1); the operation is `done`; every input the reverse needs was
on disk before the effect (LOG-2); and the reverse is itself an operation this frame allows. In
every other case the record says "no way back" with one reason from this list: the row declares
none; found already so; not proven; an input is missing; done by the owner.

Test on fakes: for each final status other than `done`, the record's way-back field is "none" with
the matching reason, and a restore built from that journal holds no reverse for it unless EV-5 says
otherwise.

**EV-5. What a restore offers.** A restore builds its manifest from the retiring run's journal, by
each operation's final status.

| Status in the retiring run | The restore |
|---|---|
| `done`, with a way back on record | offers the reverse |
| `not proven` | lists it. It offers the reverse only if the owner asks for that line in the restore's look; every form then says it runs on his word and was not proven the run's |
| `already so` | offers no reverse and lists it as left as found |
| `done by owner`, in either mode | offers the reverse as an owner step in the same mode |
| a keep | reverses nothing; it may copy from the keep (KEEP-4) |
| any other | offers nothing and lists it |

Every reverse is an ordinary operation under every rule of this frame. A reverse that needs the
output of a reverse that is not offered is planned by ORD-2.

Test on fakes: from a sunset journal holding one operation of each status, the restore's manifest
holds exactly the reverses this table names; the `not proven` reverse appears only with the owner's
answer, and its form line says so.

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
changed and no file text in any output; a removed schedule line between two different environment
lines returns between them, and with a line inserted above it the restore stops; an alias line
returns at the end of the shortcut file only when its name is free.

**EV-7. A restore is a run.** It has its own look, manifest, preview, go, journal and phases
(ORD-4), and never runs the retiring run's order backwards. It reads the journal of the project
key's latest retiring run, whatever that run's ending; if that run is open, the restore's go closes
it. Where a protected record or a keep that the restore needs is missing or fails its fingerprint,
the operations that need it are planned `not applicable` with that reason, and the rest are still
offered.

Test on fakes: a restore over a sunset that stopped after its barrier reverses exactly the
operations that are `done` with a way back, and that sunset run is `closed` once the restore has its
go; a missing protected record takes only its dependents out of the offer.

### 3.5 Order

**ORD-1. Outputs, needs, and what meets them.** Every operation provides one named output. An
operation's needs are written against output names, each at one level, and it runs only when every
need is met.

| Level | Met when the output's provider is |
|---|---|
| state | `done`, `already so` (at planning or in the run), `not proven`, `adopted`, `done by owner, read back`; and `done by owner, on his word` only where the need is marked as accepting his word |
| made | `done` |
| passed | `passed`; and `unavailable` only where the need is marked as accepting it |
| answered | `answered` |

The final statuses are: `done`, `already so`, `not proven`, `adopted`, `passed`, `unavailable`,
`refused`, `done by owner, read back`, `done by owner, on his word`, `answered`, `left`,
`not needed`, `held`. An operation whose need can no longer be met, because the provider ended
`left` or `held`, is recorded `held`.

Test on fakes: a table-driven test over every pair of status and level asserts run or not run as
this table says.

**ORD-2. A need on an output that nothing provides.** When a manifest is built, a need that names an
output no operation in it provides is settled then, by the treatment the row declares for that need:
`then not applicable` (the needing operation is left out as well, and so on down the line) or
`then not needed` (the need is dropped). A need at the state level is instead met outright where the
look read that state as already holding. A need at the made level on an output that only an adopt
provides counts as unprovided. A need with no declared treatment, a need left pointing at nothing,
or a circle of needs, fails the build and names the row. Nothing about the shape of the plan is
settled after the go.

Test on fakes: the manifests built for every combination of project type and flag over a lane's rows
either hold no need that points at nothing, or fail at build with the row named; none fails for this
reason during a run.

**ORD-3. Conditions and alternatives.** An operation may carry one condition. A condition on a
planning fact is settled when the manifest is built: the operation is `in` or `not applicable`. A
condition on an alternative result of an earlier operation of the same manifest is settled when that
operation ends: true, the operation can run; false, it is recorded `not needed`. An alternative
result is a definite refusal the provider module declares (SEC-4), named in the row, and each one a
row names is the condition of at least one operation. Several operations may provide the same output
as alternatives: the output is established when one of them reaches a status that meets a need and
each other one is `not needed`. Two alternatives that could run at the same time fail the build.

Test on fakes: with a provision that answers `terms`, the terms step and the second provision run
and the dependents run once, after it; with a provision that succeeds, both are recorded
`not needed` and the dependents run once; in neither does a dependent run before the output is
established.

**ORD-4. Phases.** A lane declares its manifest's phases in order and puts every operation in one.
No operation of a phase starts until every operation of every earlier phase is final and that
phase's gate, where this frame gives it one (KEEP-3), holds. Inside a phase only needs order the
work, so an operation that waits on the owner holds back its dependents and the next phase, and
nothing else.

Test on fakes: with an owner step waiting in one phase, every operation of that phase that does not
need it still runs and no operation of a later phase starts; in a retirement no provider retirement
call is recorded before the last machine retirement is final.

**ORD-5. One at a time, in a fixed order.** An invocation runs one operation at a time: the first,
in the manifest's order, whose phase is open, whose condition is true and whose needs are met. When
there is none, it ends (RUN-12).

Test on fakes: two runs of one fixture record the same sequence of calls; no two effect calls of one
run overlap in the fakes' records.

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
holds a partial keep.

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
different database than the one to be idled stops before the idle.

**KEEP-3. The barrier.** No operation that retires anything starts unless, in the same invocation,
every keep in the manifest is `done` and has just been checked again in full: at its place, with the
permissions SEC-7 requires, of the recorded size and fingerprint, and passing the content checks its
row declares. A failure stops the run with nothing further retired.

Test on fakes: a dump cut short between two invocations stops the resume at the barrier with every
fake still live and every path where it was; the same cut made after some retirements are done stops
the resume before the next one.

**KEEP-4. Keeps stay.** No operation of any run changes, moves or removes a keep.

Test on fakes: after a sunset, a restore and a second sunset, every keep of the first is at its
place and equal to its recorded fingerprint.

**KEEP-5. A run's last record.** Where a lane has a run write its own record among the project's
things (a sunset's tombstone, a restore's entry), that operation is alone in the last phase, runs
only when every other operation of the manifest is final, is rendered from the journal alone, and is
written once. A run that is `waiting`, `stopped` or `closed` has written none. The project's record
is a history: each run adds its own entry and never rewrites, refreshes or removes an entry an
earlier run wrote, and an earlier run's entry at the place is not a collision.

Test on fakes: with the database step waiting, no tombstone exists anywhere; once the step is read
back the tombstone is written once and shows the final state; a second sunset after a restore adds
an entry and leaves the first byte-equal.

### 3.7 Secrets

**SEC-1. Three classes of content.** Content is protected until a line of this table makes it safe.
Only safe content may appear in the journal, a manifest, a form, the CLI's output or an error;
secret and protected content rest only where SEC-7 allows and travel only by SEC-2.

| Class | What it is |
|---|---|
| secret | a provider's token; a database password; a value of an env file; a key or certificate file; the data in a dump |
| protected | content the run read from the owner's files or from a tool and has not validated: a schedule's command, a launch agent's file, a memory note, the before-image or after-image of a span, the present text of a file |
| safe | text the tool itself wrote from validated inputs; a validated field (SEC-4); content that a validator the row declares has passed; the owner's own words given in this run and validated (SEC-9) |

Test on fakes: a canary planted in each secret source and each protected source appears, by the scan
of SEC-11, in no journal line, manifest, form, output or error.

**SEC-2. Channels.** The hosting token is read in-process by one function, from the environment
variable, else from the hosting tool's own credentials file opened read-only (the owner's ruling,
A2). It is used only in requests the frame itself makes to the provider's fixed host, over TLS,
following no redirect and logging no request, and is then dropped. The database password travels to
the dump tool in a private password file: built in the run directory, owner-only from its first
byte, named to the tool by a path in its environment (SEC-3), and removed when the tool ends and at
the start of the next invocation if a kill left it. The database address's host, port, database name
and user name are safe content. The git host's tool keeps its own token; the frame never reads it.
A protected record that an adapter needs (a routine's definition to recreate) is handed over as the
path of a private file, never as an argument and never in the CLI's output.

Test on fakes: the fake host records that the authorization header arrived with the right hash and
that no redirect was followed; the fake dump tool records the password file's path in its
environment and finds the file owner-only, and the file is gone after the call and after a kill and
resume.

**SEC-3. The child process.** Every child is started by one runner, and only as this table says.

| Aspect | Contract |
|---|---|
| command | an argument list built from the row's declared template, filled with validated inputs and output fields; never a shell line |
| environment | built from nothing. It holds the base names `HOME`, `PATH`, `USER`, `LOGNAME`, `LANG` and `LC_ALL` (the last two set to one fixed locale) and `TMPDIR` (set to a private folder in the run directory), and the names the provider module registered for that command, each of one class: fixed (a safe literal); passed (copied from the session, only for a name registered with its reason, never for a name the module lists as carrying a credential); private path (the path of an owner-only file the frame made). Nothing else of the session reaches a child |
| refusals | the runner refuses: a command with no declaration; an argument on the tool's registered list of debug, verbose and trace flags; any argument or environment value that holds a registered secret, whole, by component, or in the percent-encoded or base64 form of either |
| files it makes | a file-creation mask that gives every new file to the owner only; the working directory the row declares |
| input and output | standard input empty; both output streams captured in memory up to a fixed size and handed only to the parser of SEC-4; output over that size is discarded and the result is `malformed` |
| lifetime | its own process group; a time limit from the declaration; at the limit, or when the invocation is ending, the runner ends the group it started and nothing else |

Test on fakes: the fake records its arguments and the names of its environment, and the names equal
the base list plus the registered names; a session debug variable and a session token variable are
absent; a secret planted in an argument is refused before the start; a file the fake creates is
owner-only; a fake that hangs is ended at its limit and the result is `timeout`.

**SEC-4. What a provider's result may carry.** A provider module declares, for each command, its
result fields, each with a name and one type from this list. The frame keeps a field only if it is
declared and its value passes the type's validator, and keeps nothing else.

| Type | Validator |
|---|---|
| exit | an integer |
| kind | one of `not-found`, `auth`, `conflict`, `terms`, `timeout`, `malformed`, `other` |
| id | the provider's identifier: an alphabet and a length limit the module registers |
| state | one of the words the module registers for that command |
| count | a non-negative integer |
| name | a key name or a resource name: letters, digits and the punctuation the module registers, with a length limit |
| hash | a fingerprint in a registered form |
| time | a timestamp in one registered form |
| address | a link whose host and path match a pattern the module registers for that command, with no user part |
| flag | true or false |

An undeclared field is dropped. A declared field that fails its validator, a required field that is
missing, or any value that holds a registered secret in a form SEC-3 names, turns the whole result
into kind `malformed` with no value kept. The module also declares, per command, which results are
definite: the success that proves the effect happened, and the kinds that prove it did not.

Test on fakes: a fake that adds a field, mistypes one, omits one, or echoes a canary inside one: the
first is dropped, the others yield `malformed`, and no value from such a result is in the journal.

**SEC-5. Nothing a tool prints is kept or shown** (the owner's ruling, A4). What the owner or the
executor sees of a failure is the operation, the kind, and the command with its declared arguments,
so that he can run it himself and read the tool's words in his own terminal. An exception is
reported as its type and the operation; its message is never printed.

Test on fakes: a fake that fails echoing a canary whole, in part, encoded, and split across reads
leaves it in no output, form or file; a planted exception whose message holds the canary is reported
by type alone.

**SEC-6. A protected record is named, never shown.** It is a file in the run directory's protected
folder. The journal, a manifest and a form refer to it only by: an id the run assigns, never derived
from the content; its type (before-image, after-image, definition, line, values, copy); a label the
tool wrote from safe content; and a fingerprint keyed with a random value made for the run and kept
only in that folder. Where the owner must have the content (to recreate a schedule by hand, to judge
a merge before he answers), the form names the file's path and says he opens it himself; a file made
for him to read before an answer is a review file, kept in the same folder on the same terms.

Test on fakes: for a schedule whose saved command holds a canary, on a harness with no capability to
recreate it, the owner's step names a file path and a label, and the canary is in no form or output;
the journal's fingerprint of that record is not the plain hash of its content.

**SEC-7. Where a secret or a protected record may rest.** These places and no other. Each file among
them is built in staging and published (OP-3, C1), is owner-only from its first byte unless the
table says otherwise, and is never reached through a symbolic link. A place found with wider
permissions than this table gives is a failure.

| Place | What rests there | Terms |
|---|---|---|
| the frame's own memory | the hosting token; values on their way to a file | dropped after use |
| the private password file | the database password | while the dump tool runs (SEC-2) |
| the protected folder of the run directory | protected records, review files, the fingerprint key | kept with the run |
| staging | a secret-bearing object while it is built | until it is published or removed |
| the pulled env file in the working tree | env values | ignored by git, proven before every commit (SEC-10) |
| the sunset folder beside the archived repository | the dump, the saved hosting env values, the memory copy, a launch agent's file moved there | an owner-only folder outside every working tree (the owner's ruling, A2); a moved file keeps its own permissions inside it |
| the place a thing was taken from, on a restore | the working memory store copied back from its keep; a launch agent's file moved back; a span put back into its file (EV-6); a routine recreated through the adapter (SEC-2) | the original place and no other, with the permissions recorded at the retirement and never wider |
| the provider | the token in the authorization header; the password, to the database server | the authorized transmissions of SEC-2 |

What a tool writes into its own folders is not on this list: it is risk RK1 (RISK-1).

Test on fakes: after clean runs of sunrise, sunset and restore the canary is found only at these
places, each with the permissions this table gives; a link planted at any of them fails the
operation with nothing written through it.

**SEC-8. A secret-bearing output is private from its first byte.** A tool writes a secret-bearing
output only into staging; the frame checks it there and publishes it. A tool that cannot be pointed
at a staging path, or whose own secret-writing side effect cannot be turned off, is not run for that
purpose.

Test on fakes: the fake hosting tool's pull writes into a staging path, and the env file appears in
the working tree owner-only and complete; a fake that can only write in place is never started.

**SEC-9. Inputs are validated before they are stored.** An input that holds a secret (an address
with a password in it, a description that holds a registered secret) is refused at the start and is
stored nowhere.

Test on fakes: a summons with a password inside an address ends refused, and the canary password is
in no file of the fixture home.

**SEC-10. Nothing is committed or pushed unscanned.** Before every commit a check scans, by content,
exactly what will be committed and proves the ignore rule; before a push a check scans every commit
to be pushed. A hit stops the run, names the file and shows nothing.

Test on fakes: a canary in a file about to be committed stops the run before the commit; a canary in
an earlier commit stops it before the push; in both the output names the file and holds no canary.

**SEC-11. How the secret rules are tested.** A marked canary, built at run time, is planted in every
source SEC-1 names. The scan covers every file under the fixture home and the fixture working tree,
both output streams, every argument and environment that every fake recorded for itself and for
anything it started, and every git object. It looks for the canary whole, for each of its
components, and for the percent-encoded and base64 forms of both. A canary found outside a place of
SEC-7, or at one with wider permissions, fails. The fake host records only that an authorization
header arrived and whether its hash is the expected token's; it never stores the header.

Test on fakes: the scan is itself proven: a canary planted in each scanned place, in each form, is
found.

### 3.8 Forms

**FORM-1. Where a form's text comes from.** A form is a file in the run directory, named in the
CLI's output and shown by the adapter. Its text comes from four sources only: v1's fixed text for
that form, the lines of FORM-2, text the tool wrote from validated inputs and fields, and the
owner's own words.

Test on fakes: with a canary in every protected source and in every tool's output, each form of each
run is rendered and holds no canary; a form template that reads a file's text directly fails its
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

Test on fakes: a run driven through every status renders every form with the matching line; a form
template that lacks one of these lines fails its build test.

**FORM-3. A restore has forms of its own.** A restore has a preview, a status form, a summary, and
its entry in the project's record (KEEP-5). They are forms under FORM-1 and FORM-2, and are not
changes to a v1 form.

Test on fakes: a restore run renders each of the four.

### 3.9 What a row states

**ROW-1. A row states all of this, or the manifest is not built from it.**

| A row states | Used by |
|---|---|
| its id, kind and phase | OP-2, ORD-4 |
| the thing it acts on: its role, how its identity is read, and its tracked state; or the output field it refers to | RUN-6, EV-3 |
| its planning test | RUN-6, RUN-7 |
| its before-test and its after-test | OP-5 |
| its construction; for C2 and C5 the document cited; for C3 and C6 the accepted risk | OP-3, RISK-1 |
| its one effect as a declared command: the argument template, the registered environment names, the time limit, the result fields, the definite results, the alternative results | OP-1, SEC-3, SEC-4, ORD-3 |
| each command that can change a repository | OP-11 |
| its after-check | OP-6, EV-1 |
| the output it provides and that output's fields; each need, with its level and its treatment when nothing provides it; its condition | ORD-1, ORD-2, ORD-3 |
| for a create: how a lost answer can be resolved, with the provider's document, or "by the owner only" | OP-7 |
| its way back, or "none" with the reason; for a span, its placement and whether the file is ordered | EV-4, EV-6 |
| for an owner kind: its mode, the safe content its step is built from, the answers it allows, any review file | OP-9, SEC-6 |
| for an output that may be adopted: that it may, and how the owner names the thing | OP-10 |
| for a keep: its scope, how the inventory and the copy share one state, and its content checks. For a retirement: the keeps it requires | KEEP-1, KEEP-2, KEEP-3 |
| the class of every content it reads, stores or shows; any validator that makes content safe; each resting place it uses | SEC-1, SEC-7 |
| its lines in each form | FORM-2 |

Test on fakes: for each kind, a row with each required entry removed in turn fails the manifest
build and names the entry.

## Part 4. The risk that is left

**RISK-1. The accepted risks stand as the catalog's Part 6 states them.** RK1 (the tools' own
files), RK2 (a file changed by something else in the instant of a swap) and RK3 (a provider state
changed by someone else in the instant of T20, T21, V10 or V11) were accepted by the owner (the
contract's section 18, A4). This frame removes none of them and adds none. RK2 is read as covering
the swap, C3, wherever a row uses it. An operation carried under RK2 or RK3 is marked so in the
journal.

Test on fakes: every operation built by C3 or C6 carries the mark, and no other operation does.

**RISK-2. A window nobody accepted is not the tool's to take.** Until the owner rules on it, a row
whose effect has such a window is written as an owner step (OP-9), and a manifest that holds it as a
tool's effect fails its build. Known today: C7, which is every move of an identified thing; C6
outside the four rows RK3 names; a schedule table that can only be read and then replaced through
its own tool, which no construction of OP-3 covers; and a before-test condition on something the
effect does not change, which no construction enforces (today: a shortcut's name being free among
the shell's commands). The frame's one assumption (RUN-4) is likewise the owner's to accept, and is
put to him with these.

Test on fakes: a manifest that holds a move as a tool's effect fails its build while C7 is closed,
and names the row.

## Part 5. Worked examples (illustration only; the rules are the source)

One draft row of the catalog's Part 4 for each of the nine kinds, walked through a kill at each
boundary and the resume that follows. The rows are drafts: a lane may write them differently. Each
line gives what is on disk and in the world, the probe's answer, the move, and the rules applied.

### Example 1. check: the scan before the push (draft row SR14)

It needs the kit check `passed`. Its subject is every commit to be pushed.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the result line | no record of the check | the check is made from the start | OP-8 |
| after the line `passed`, naming commit c2 | a pass on record from the killed invocation | the push needs a pass made in its own invocation: the scan is made again on c2, then the push is probed | OP-8, SEC-10 |
| variant: the pass is on record, and a commit c3 that no operation of the run made is now the branch's head | the branch is not in its last tracked state | `foreign`: stop, naming the repository | EV-3 |
| variant: the scan finds a hit | no pass | `failed`: stop, the file named, nothing shown | SEC-10, RUN-12 |

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
| after the start record, before the send, or after the send with no answer | a start record and no answer; the repository may or may not exist | outstanding: stop. The row cites the provider's unique names, so a re-plan may plan the create again, its preview saying an earlier send got no answer. If the name is then taken: a planning stop, and the repository there is not proven the run's | OP-7, RUN-11 |
| after the answer's id is on record, before the completion record | the id in the journal | the after-check by that id, then completion: `done` | LOG-2, OP-6 |
| after the completion record | `done` | not probed | EV-3 |
| variant: the answer is `conflict` | a definite refusal, nothing made by this call | stop: something has the name | OP-6 |

### Example 4. change: remove the shortcut lines (draft row T11)

Built by C3 under RK2. The start record holds the file's hash, each line and the lines on each side
of it as protected records, and the after-image.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the start record | the file as the look read it | `ready` | OP-5 |
| after the start record, before the swap (with or without the staged file) | the lines still in the file | `not landed`: any staged file is removed; a new start record; the swap again | OP-6 |
| after the swap, before the completion record | the file in place has the staged identity on record | `landed`: completion on ground (b), with its way back recorded | OP-6, EV-1, EV-4 |
| variant: killed before the swap, and the owner then deletes the lines by hand | the after-state holds; the file in place is not the staged object | `landed`: `not proven`; the run goes on; no way back is recorded, and a restore asks before reversing it | OP-6, EV-4, EV-5 |
| variant: a program that ignores the lock rewrites the file after the probe | the hash differs at the swap | the swap is not made: stop. On resume the probe reads the file again | OP-3, RISK-1 |

### Example 5. move: the repository to the archive folder (draft row T12)

C7 is closed today (RISK-2), so today this row is an owner step in read-back mode: the form shows
the exact move, the tool's read (the target holds the identity on record and the source is absent)
completes it as `done by owner, read back`, and a restore offers the reverse as an owner step. The
table shows the same row as a tool's move, which is what it becomes if the owner opens C7.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the start record | the repository at its path, with the head the look recorded | `ready` | OP-5 |
| after the start record, before the rename | the same | `not landed`: a new start record; the rename again | OP-6 |
| after the rename, before the completion record | the source absent; the target holds the identity on record | `landed`: `not proven`; the run goes on, later operations reading the new path from this record; a restore asks before reversing it | OP-6, EV-2, EV-5 |
| variant: killed before the rename, and the owner then moves the folder by hand | exactly the same as the line above | the same: `not proven`. The run does not claim the move | EV-1 |
| after the completion record | `done`, with its way back recorded | not probed | EV-3, EV-4 |
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
| a kill before the `waiting` line | no record | probed again; the `waiting` line and the step are written | OP-9 |
| waiting; he pauses it in the dashboard and says done | `waiting` on record; the provider reports paused | the read shows the after-state: `done by owner, read back`; the last record can now be written | OP-9, KEEP-5 |
| waiting; he says done, and the provider still reports live | `waiting` | it stays `waiting`; the form says what the read showed | OP-9 |
| waiting; he says nothing; a later invocation's read shows paused | `waiting` | completed by the read | OP-9 |
| waiting; he answers "leave it" | `waiting` | `left`; the run ends with exceptions and its last record lists the step as left | OP-9, RUN-12, KEEP-5 |
| while it waits | every other operation of its phase that does not need it has run | the tombstone has not been written | ORD-4, KEEP-5 |

A restore offers the reverse as an owner step in the same mode (EV-5).

### Example 8. owner answer: approve a merged kit file (the draft's SR03a)

The merged candidate is built in staging and a review file is made; the form names its path. The
answers the row allows are "use it" and "stop here". The swap that follows needs the answer.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the `waiting` line | no record | the candidate and the review file are built again; `waiting` | OP-9, SEC-6 |
| after the `waiting` line | the review file in the protected folder | still `waiting`; the form names the file again | OP-9 |
| after his answer is on record | `answered` | not asked again; the swap is probed | EV-3, ORD-1 |
| his answer line cut off | the last line discarded | asked again | LOG-1 |
| variant: he answers "leave it" | `left` | the swap is `held`; the run ends with exceptions | ORD-1, RUN-12 |

### Example 9. adopt: the project folder under `--promote` (draft row SR01, its second case)

The owner's input names the folder. The look reads its identity and tracked state; the manifest
holds an adopt for the output "project folder" in place of the build, and the preview shows the
identity.

| Kill at | On disk and in the world | Resume | Rules |
|---|---|---|---|
| before the `adopted` record | the folder as the manifest recorded it | probed again; the record is written; nothing in the folder changes | OP-10 |
| after the `adopted` record | `adopted` | not probed; operations with state needs on the folder run | EV-3, ORD-1 |
| variant: the folder changed between the go and the adopt | not as the manifest recorded | `foreign`: stop | EV-3 |
| variant: no input named the folder, and the look finds it at the planned place | a thing at the place | a planning stop; no adopt is planned | RUN-7, OP-10 |
