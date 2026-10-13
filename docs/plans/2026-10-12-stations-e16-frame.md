# E16 frame: the executor's rules, the proof a run may claim, and how a secret travels

Written 2026-10-12 by a new author, on the owner's word (the lane contract
`docs/plans/2026-10-11-stations-e16.md`, section 18, A5), from the outside reviewer's three design
reads. **This document is the single source for the frame.** It replaces Parts 1 to 3 of the
operation catalog (`docs/plans/2026-10-12-stations-e16-operations.md`): the rules X1 to X13, the
evidence classes E1 to E4 and the secret rules K1 to K8 are withdrawn. The owner's rulings (the
contract's sections 5 and 18) stand above this document. This document stands above every lane's
rows: a row that cannot be written under these rules is not written, and the lane stops and asks.
**Status: under the outside reviewer's checks; the contract's section 18 records each round, and
this text does not say that the rules hold. No slice has the owner's go.**

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

**RUN-1. Every invocation starts the same way.** In this order: the gate (first the withheld read
of SEC-12, before anything is printed, then the vault and machine checks); the locks, which is the
name check, every lock RUN-2 has it take and each look for an open run (RUN-3), in the order RUN-2
gives; the run directory opened, or made for a new run (RUN-4), and, for a run that is continued,
the read of its disproof records (SEC-12); then the reads its kind of summons makes. A first look
and a re-plan make the whole look (RUN-5). An invocation that goes on, or that only renders status,
makes the reads RUN-10 and OP-9 order and no other. A close makes none. SEC-12's table gives this
line by line. Nothing comes before the gate, the cue included. A failed gate ends the invocation
with nothing created and no lock taken; a name that fails its check, a held lock, and an open run
that turns a new summons away, end it with nothing created. Once the startup checks have passed, an
invocation's first journal records are written in the one order SEC-12 gives, and in no other.

Test on fakes: with no vault, with a stub vault, and with a vault inside a synced folder, the
invocation ends refused, the fixture home is byte-equal to before, no lock file exists and the cue
fake recorded no call; on a sound fixture vault the gate passes and the fakes' records show the
gate, its withheld read before any output, then the name check, then the first locks and the early
look for an open run, then for a new summons or a re-plan the alias reads, the later locks and the
second look for an open run, then the run directory with, for a continued run, the read of its
disproof records, then the reads, in that order; a close records no runner call, and a status-only
summons no planning read; an invocation of a retirement that owes at once a disproof record, a
receipt and EV-7's closing record writes those three in that order before any other record.

**RUN-2. One lock per project key.** The project key is the project's name folded: lowercased, with
every character that is not a letter or a digit removed. A key is written nowhere as it is. What
the tool writes of one, in a lock's file name, in a lock's record, in the record of open runs and in
the journal's record of a run's opening (RUN-3), is its fingerprint, keyed with a random value the
tool makes once on this machine and keeps in an owner-only file of its own beside the run
directories (SEC-7). Neither a name nor a key is written in a lock's file name, a lock's record or
the record of open runs. The gate fails where that file is not owner-only, or is missing while a
lock's file or the record of open runs exists. The refusal then says, in the tool's fixed text and
with nothing else but run ids: which of the two it found; where the file is kept; and the id of each
run that a lock's record or the record of open runs holds. It prints all of this as SEC-12's
withheld read lets it. A run whose id may not be printed is still listed: by the fixed words of
withholding and the name of the file whose record holds its id, which he opens himself to read it.
So he knows every run on record, as before. The ways on are steps of his, and the
tool takes none of them for him. Where the file is not owner-only, he makes it owner-only and
summons again. Where it is missing, he puts it back from a copy of his own and summons again. Where
he has no copy, the one way left is a decision that is his alone: he ends by hand each run the
refusal listed, removes the lock files and the record of open runs himself, and summons again, and
the tool then makes a new value. From then on the tool sees none of those runs: it can neither
resume nor close them, and it does not refuse a new run on a project that one of them had open. The
tool never makes a new value while a lock's file or the record of open runs exists.

RUN-1's second step runs in this order, all of it before a run directory is opened or made.

| Part | What is done | What it reads |
|---|---|---|
| (a) the name check | every name the summons carries, the one it was summoned with and each further name the owner gave, is checked in memory: it must hold no entry of the register, into which the invocation first reads each secret SEC-2 lets it read without the project (the hosting token). A name that fails is refused with the tool's fixed text: nothing of it is written, in any form, no lock is taken and nothing is created | the token's channel; nothing of the project |
| (b) the first locks | the lock of the key of each of those names, in sorted order. Where the machine has no keying value yet, it is made now, by a create that fails if another invocation made it first | each lock's own record |
| (c) the early look for an open run | under the keys of (b). A new summons that finds one is refused here (RUN-3). A summons that continues a run takes from the record the other keys that run is open under, and their locks, in sorted order | the record of open runs; nothing of the project |
| (d) the alias reads | for a new summons, which is one that continues no open run, and for a re-plan, and for no other: the reads of this machine's own files that the lane's rows declare as showing another name form of the project, made in-process, with no runner and no provider | those files, and no other thing of the project |
| (e) the later locks, and the second look for an open run | the lock of the key of each name form (d) showed, in sorted order; then the look for an open run under those keys, which refuses a new summons as (c) does | each lock's own record; the record of open runs |

Where a provider's answer later shows the project under a name whose key the invocation does not
hold, no lock is taken under that name. The look ends as a planning stop does (RUN-7, RUN-12):
`refused` before a first go; `stopped`, with the manifest in force unchanged, in a re-plan of a run
that has its go. Either way the form says that a provider shows the project under another name and
names the private file that holds it (SEC-6), and the owner summons again and gives that name too
(the owner's ruling, A21). A lock is of the kind the system releases when its holder dies, and is
never broken by age. An invocation never waits for a lock: one that meets a held lock ends at once,
names the run that holds it by the id in the lock's record, where SEC-12's withheld read lets that
id be printed, and reads nothing more. At a first lock
it has read nothing of the project; at a later lock it has read the record of open runs and, of the
project, what the alias reads read and nothing else. A file that the runs of other projects also
change has a lock of its own, held only around the one change (OP-3, C3).

Test on fakes: of two invocations summoned with two spellings of one name (a different case, a
hyphen against an underscore), the second ends on the lock with no probe call recorded; of two
summoned with names that fold to different keys, where the first's alias reads showed the second's
name, the second ends on the lock the same way; the lock fake's record shows the added keys taken in
sorted order and no wait, and every lock taken before a run directory is opened or made, so that a
held lock on a later key ends the invocation with nothing created; a refusal at a first lock
records no read of the record of open runs but the gate's withheld read's, and none of the project,
and a refusal at a later lock records, after the gate's, the early look's read of the record of open
runs, the alias reads the fixture's rows declare and no other
read of the project; of two summonses under names that fold to different keys, where only a fake
provider's answer shows them to be one project, the second's first look ends `refused` with the
other name in a private file and in no output, and with no lock taken under it; summoned again with
both names, it meets the first's lock or its open run and is refused naming that run; the same
answer met in the look of a re-plan of a run that has its go ends that invocation `stopped`, with
the manifest in force byte-equal and the same form line; after the first is killed a third takes the
locks and goes on; two runs of different projects that change one shared file both land their
change. The names: a summons whose name is a canary equal to the fixture's hosting token, and one
that carries that canary as a further name, each end refused with fixed text, and the fixture home
then holds no lock file, no lock record and no new file; a summons whose name is a canary that
equals no secret the tool can read before the project takes its locks and, after its go, is recorded
as open, and the canary and its folded form, whole and in each form SEC-11 names, are in no lock's
file name, no lock's record and not in the record of open runs, which hold fingerprints and run ids
only; two
fixture machines give two different fingerprints for one name; with the keying value's file removed
while a lock file exists, the gate fails, its output being fixed text that names what it found, the
file's place and the ids of the runs on record, and no new value is made; with the file put back the
next summons passes the gate; with the lock files and the record of open runs removed by the
fixture's owner the next summons makes a new value; with the file given wider permissions the gate
fails, and it passes once the file is owner-only again. A caught id: two fixture runs are open; a
fake returns the first run's own id in a secret field, and that run records its disproof and stops.
The keying value's file is then removed, and in a second pass given wider permissions, and a resume
of the first run is summoned. In both passes the gate's output lists the second run by its id and
the first by the fixed words of withholding and the name of the file whose record holds its id; the
first run's id is in no output; nothing in either run directory has changed; and the file the output
names does hold that id, so the fixture's owner can end both runs by hand as before.

**RUN-3. One open run per project key.** A run is open from its first go (RUN-9) until it ends
`complete`, `ended with exceptions` or `closed` (RUN-12). At the go the run is recorded as open
under every project key it holds the lock of, in one write that records all of those keys or none
of them, made together with the record of the go; a re-plan whose alias reads show a further key
adds it the same way with its own go. A key is recorded there by its fingerprint (RUN-2). Every
summons looks for an open run twice, where RUN-2 places each look: early, under the keys of the
names it carries,
having read nothing of the project; and again under each key its alias reads show, having read only
those files besides. Both are made before a run directory is opened or made. While any of those
keys has an open run, the summons may only resume it (RUN-10), re-plan it (RUN-11) or close it
(RUN-13); any other summons is refused and names the open run by its id, where SEC-12's withheld
read lets that id be printed. The one exception is in EV-7.

Test on fakes: with a sunrise left `waiting` that holds a second key, a sunset summons
under either of those two names is refused at the early look with the open run named, having read
the record of open runs and nothing of the project or of a provider; a sunset summons under a third
name, which only the fixture's alias reads show to be the same project, is refused at the second
look with the open run named, having read the record of open runs and the files the fixture's rows
declare for the alias reads, and no other thing of the project or of a provider; each has made no
file and no folder; a kill between the go and the opening record leaves the run open under all of
its keys or under none; and a resume, a re-plan, a close and a restore of that run (EV-7) are each
accepted.

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
capabilities); the journals of the project key's earlier runs, each read as SEC-12 has another run's
journal read; the planning facts of RUN-6; and the
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
| planning stop | the place is taken by a thing this run's journal does not show the run made; the thing is in neither state the row names; the read failed, was partial, was made as the wrong account, or ran out of time; a provider shows the project under a name whose key is not held (RUN-2); a secret the look needs is in no file on this machine (SEC-12) | the invocation ends before any preview and names each; nothing is approved; RUN-12 names the ending, `refused` before a first go and `stopped` in a re-plan |

Test on fakes: on a clear fixture every candidate is planned `in` and a manifest is written; each
planted condition of a never-clobber fixture (an existing folder, an existing remote, a taken name
at the host, a shortcut that shadows a program) ends the look with the condition named and no
manifest; so does each of a failed read, a partial read, a read made as the wrong account and a read
that ran out of time, each named; a provider resource that is already retired yields a preview line
and no operation.

**RUN-8. The manifest is the plan, and the preview is the manifest.** A manifest holds: the inputs;
the accounts, capabilities and machine locations the look read; the phases (ORD-4); every operation
with everything its row states (ROW-1), its planning outcome and the tracked state read; and every
`already so` and `not applicable` line. Every value in it is marked as one of three things: a
literal, which is safe content (SEC-1); a reference to a protected record, for a value the look read
that no ground of SEC-4 proved (SEC-6); or a reference to an output's field (RUN-6). The preview is
rendered from the manifest and from nothing else. A manifest never changes once it has its go.

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

**RUN-12. How an invocation and a run end.** An invocation of a run that has a go on record runs
operations (ORD-5) until none can run or a rule says stop, then ends in exactly one of five ways,
and each ending renders a status form from the manifest and the journal, but for a stop by RUN-4's
checks, which writes only what SEC-12 allows before the startup checks pass. What SEC-12 has
withheld is rendered in that form as SEC-12 says, never as text. An invocation that RUN-10 has end
with no effect ends in the way the run already stood, `waiting` or `stopped`, and its status form
says so. Before a run's first go there is no open run, nothing to resume, and none of the five. An
invocation that ends then ends in one of two ways: with its preview rendered, awaiting his go; or
`refused`, where the gate fails (RUN-1), a name fails its check, a lock is held or a run is open
(RUN-2, RUN-3), a planning stop is met (RUN-7), an input is refused (SEC-9), an answer is lacking
(RUN-5) or a safe ground is disproved (SEC-12). A refusal is always given in the CLI's output. At
the gate, at the name check, at a held lock, the first key's or a later key's, and where RUN-3 turns
a new summons away, that is all of it: nothing is created, no file and no folder, and the output is
the tool's own fixed text naming the failed check, the run that holds the lock or the run that is
open (SEC-12). On every one of these paths, and on a stop by RUN-4's checks, the fixed text and each
run's id are printed only as SEC-12's withheld read lets them be: a value a run has caught is in
none of them. A refusal after RUN-1's third step is also rendered as a refusal form, a file in the
run directory that step made or opened, from the summons's validated inputs and from what the look
had read by then, naming each cause. A refusal writes no manifest and no journal, and the next
summons
starts a new look. A summons turned away at the gate, at a held lock or by RUN-3 is `refused` in the
same way whether or not the run it names has a go, and changes nothing in that run, but for the one
closing record EV-7 has it write. A planning stop, a refused input or a lacking answer met in the
look of a re-plan, in a run that already has a go, ends that invocation `stopped`, with the manifest
in force unchanged.

| Ending | When | The run is then |
|---|---|---|
| `complete` | every operation is final (ORD-1) and none is `left` or `held` | ended |
| `ended with exceptions` | every operation is final and at least one is `left` or `held` | ended; each exception is listed with its reason |
| `waiting` | nothing can run and at least one operation waits on the owner | open; each waiting step is listed with its exact step and its mode; the locks are released |
| `stopped` | a rule of this frame says stop; or nothing can run, nothing waits on the owner, and an operation is not final | open; the form names the reason kind, the operation where the stop is in one, what the owner can check, and the ways on: resume, re-plan, close, and for a retirement, restore over what is finished (EV-7) |
| `closed` | RUN-13 | ended |

Test on fakes: the kill sweep's reference run ends `complete`; a fixture with an owner step ends
`waiting` with the step listed and no lock held; a planted stop inside an operation ends `stopped`
with that operation named; a stop that belongs to no operation in a run that has its go (a RUN-4
failure) ends `stopped` with the cause named in the tool's fixed text, with no status form and with
nothing from the journal or the manifest in any output; a failed gate ends `refused` with the
fixture home byte-equal, so no refusal form, no run directory and no lock file, and with the CLI's
output holding only fixed text that names the failed check; a name that fails its check, a held
lock, the first key's or a later key's, and an open run met by a new summons, each end `refused` the
same way, the output naming the failed check, the holding run or the open run; a planning stop in a
first look ends `refused`, with a refusal form in its run directory naming each cause, no manifest
and no journal written, no run open under the key, and a later resume summons finding nothing to
resume; the same planning stop in a re-plan's look ends `stopped` with the manifest in force
unchanged; both are run with each cause RUN-7 lists, a provider showing the project under another
name and a secret that no file on the machine holds among them; a summons with no word on a run
left `waiting` ends `waiting`, and one on a run left `stopped` ends `stopped`, each with the status
form rendered and no effect call; a fixture with a `left` step ends
`ended with exceptions` with it listed; a closed run ends `closed`; for a run with a go on record no
ending other than these five is ever recorded. A caught value on each early path: a fixture run has
caught, with its disproof on record, its own id, and in a second pass a word of the tool's fixed
refusal text that its journal holds. A later summons is then driven to each early ending in turn: a
failed vault check, the keying value's file missing, a name that fails its check, that run's lock
held by another invocation, a later key's lock held, a new summons met by that run open at the early
look and at the second, and a stop by RUN-4's checks on that run directory after a file in it is
given wider permissions. In none is the caught id or the caught word in any output; each output
holds the fixed words of withholding in its place and, for the id, the name of the file whose record
holds it; and a run that caught nothing is named by its id on the same paths.

**RUN-13. The owner can close a run.** On his word an open run is recorded `closed`. A closed run
never resumes. Closing changes nothing outside the run directory and undoes nothing; the form lists
what was done, with what SEC-12 has withheld rendered as SEC-12 says. The close record is one more
record, written after every recovery record SEC-12's order puts before it and never in the place of
one.

Test on fakes: a close on a stopped run that owes no recovery record, given his word, records one
journal record, the close record, and no effect call; a close on a stopped run that owes a disproof
record and a receipt (the kill of SEC-12's test line between the protected record and the disproof
record) records those two and then the close record, three records in that order, and no effect
call; a close summons that does not carry his word records no close record and leaves the run open;
a later resume of the closed run is refused.

### 3.2 The journal

**LOG-1. Written ahead, durable, chained.** A journal record is appended, flushed, and synced
together with its directory before the step it describes begins; a record of an outcome is synced
before any later operation starts. Every record carries the hash of the record before it. On read, a
cut-off last record is discarded and its operation is treated as if that record had never been
written; a break in the chain anywhere else stops the invocation. The journal's records are of these
kinds and no other: the run's opening under its keys (RUN-3); a go and each later word; an
operation's start, step, answer, completion and status records; a check's attempt (OP-8); an owner
operation's waiting record and his answer; a disproof (SEC-12); an invocation's ending; the run's
ending.

Test on fakes: on a fake file system that loses every write not yet synced at a kill, a kill at
every write boundary leaves, for every effect call the fakes recorded, that operation's start record
in the journal; the journal reads back with at most its last record dropped, and the operation that
record belonged to is probed under OP-5 as if it were absent; a record of a kind this rule does not
list stops the invocation.

**LOG-2. The start record holds everything that is needed later.** Before an operation's effect the
journal holds its start record: the thing's identity and tracked state as just read, where what a
provider returned of them and no ground of SEC-4 proved is held in a protected record that the start
record refers to; the after-state the effect is to leave, computed beforehand and never read back;
and every input a reverse would
need, each as a protected record (SEC-6) where it is content: the before-image and the after-image
of a span, the lines on each side of it, the whole definition of a thing to be cancelled, the state
a provider reported. For an effect built in staging, a step record with the staged object's identity
and, for a file, its fingerprint, is durable before the publish. For a create, the provider's answer
is recorded before anything else is done with it: the id goes to a protected record as a held value
(SEC-4), and an answer record in the journal refers to it. A completion record adds only what was
observed.

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
| C2 | the id read is the id the answer record refers to (LOG-2), the two compared in memory; with no answer record the create is outstanding whatever is read (OP-7) |
| C3 | it is the file at the recorded path. The object's own identity is not asked here, because a swap and an editor both replace it; whether the object in place is the staged one is asked by OP-6 |
| C4 | it is the same named branch or tag of the same repository |
| C5, C6 | it has the provider id that the start record refers to (LOG-2), the two compared in memory, or is the named thing of this machine that the start record holds |
| C7 | the object has the identity read at the source into the start record. The before-state is that object at the source with nothing at the target; the after-state is nothing at the source with that object at the target; any other pairing of the two places is `foreign` |

Test on fakes: for each kind that has an effect, fixtures for the six answers each yield that answer
and no state-changing call; a fixture with no record in which both tests hold yields `already so`,
and one with a start record in which both states hold yields `landed`; for a swap, a file replaced
by another actor with the after-content yields `landed`, and one with any other content `foreign`;
for a build, an object with another identity at the place yields `foreign`; for a move with a start
record, the recorded object at the source with nothing at the target yields `not landed`, nothing at
the source with the recorded object at the target yields `landed`, and every other pairing (both
places hold something, neither does, or either holds an object of another identity) yields
`foreign`.

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
at the start of each invocation but a close, after its provider's identity read (SEC-12's table).
The step shown to him is built from safe content (SEC-1) by a fresh read each time, never from an
earlier form and never by repeating an effect. Where he must read
content before he answers, the row gives a review file (SEC-6). An answer that is not on the row's
list is refused and the operation stays `waiting`. The value of a recorded answer is what needs and
conditions name (ORD-1, ORD-3); an answer has no other consequence. In any mode his answer "leave
it" records the operation `left`. An owner step whose row declares a way back is shown to him as a
step to take only after every input its reverse needs (the inputs LOG-2 names for an effect) has
been read, saved as a protected record (SEC-6) and read back against its fingerprint; its `waiting`
record is written after that and names those records. Where the look finds that such an input
cannot be read, the step is planned with no way back, the preview says of that step that no reverse
can be offered, and his go covers it. Where the look could read it and the save then fails, the run
stops and the step is not shown.

Test on fakes: a step in read-back mode completes on the read alone and never on his word alone; a
step on his word completes on the word and is listed as not checked; an answer the row does not list
is refused and nothing is recorded as `answered`; a waiting step shown again after the provider's
state changed shows what the fresh read gave and not the earlier form's text; "leave it" ends the
wait as `left`; no fake records a call that performs an owner's step; for an owner step that
declares a way back, the fakes' sequence shows each input of its reverse saved and read back before
the `waiting` record and before the step is in any form, and after the owner then removes the thing
those inputs are still readable from the run directory alone; where the look cannot read an input,
the preview says no reverse can be offered for that step; where the save fails after the go, the
run stops with the step never shown.

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
received it, refers to the id (held, LOG-2) from the provider's own answer to the run's own request,
which is either the create call's definite success or the provider's documented status of that very
request (OP-7);
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
allows. The fourth is settled before the go and never after it: when the manifest is built, a
declared reverse is checked as a row of its own kind, with its construction and its accepted risks
(OP-2, OP-3, RISK-2), and a row whose declared reverse is not allowed fails the build (ROW-1). In
every other case the record says "no way back" with one reason from this list: the row declares
none; found already so; not proven; an input is missing; done by the owner.

Test on fakes: every `done` operation whose row declares a way back that passed the build, and whose
inputs are on record, has that way back recorded; a row whose declared reverse cannot be built under
OP-3 and RISK-2 (a reverse that is a read-then-ask on a row RK3 does not name) fails the manifest
build, names the row, and none of its operations runs; for each final status other than `done`, and
for a `done` operation with an input removed, the record's way-back field is "none" with the
matching reason.

**EV-5. What a restore offers.** A restore builds its manifest from the retiring run's journal. It
offers the reverse of each operation that has a way back on record (EV-4) and of no other, with two
additions the owner ruled (A6): for an operation that ended `not proven`, it lists it and offers the
reverse only if the owner asks for that line in the restore's look, and every form then says it runs
on his word and was not proven the run's; for an owner step that ended `done by owner`, in either
mode, it offers the reverse as an owner step in the same mode, where the retiring run saved what
that reverse needs (OP-9), and offers none where its preview said none could be. It may copy from a
keep (KEEP-4).
Everything it does not offer it lists, with the reason EV-4 recorded. Every reverse is an ordinary
operation under every rule of this frame. A reverse that needs the output of a reverse that is not
offered is planned by ORD-2.

Test on fakes: from a sunset journal holding one operation of each final status, the restore's
manifest holds the reverse of the `done` operation with a way back, the `not proven` reverse only
with the owner's answer and with its form line saying so, the owner step's reverse as an owner step
where its inputs were saved and none for an owner step previewed as having no reverse, and no other;
a reverse whose thing is not in the last tracked state the retiring journal holds
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
key's latest retiring run, whatever that run's ending, as SEC-12 has another run's journal read; if
that run is open, the restore's go closes it. That handover is one step with one deciding write:
the record of the restore's go and of its opening under its keys (RUN-3), which names the retiring
run it closes. Until that write is durable
nothing has changed: the retirement is open and the restore has no go. From the moment it is durable
the retirement is closed for every purpose of RUN-3, whether or not its own journal yet says so, and
a summons to resume it is refused. The retirement's own `closed` record, naming the restore, is
written next. An invocation of either run that finds it missing writes it, and may: it does so after
its gate, its locks and RUN-1's third step with RUN-4's checks, and before it refuses the summons,
runs an operation or writes any other record but the disproof records and the receipts that SEC-12's
order of first records puts before it. Where a protected record or a keep that the restore
needs is missing or fails its fingerprint, the operations that need it are planned `not applicable`
with that reason, and the rest are still offered; a receipt that is due and was not given (SEC-12)
counts as such a missing record.

Test on fakes: a restore over a sunset that stopped after its barrier reverses exactly the
operations that are `done` with a way back, and that sunset run is `closed` once the restore has its
go; a kill before the restore's go is durable leaves the sunset open and resumable and the restore
with no go; a kill after it and before the sunset's `closed` record leaves the restore open, a
resume of the sunset refused, and the next invocation of either run writing that `closed` record
after its gate, its locks and RUN-4's checks and before it refuses, runs an operation or writes any
other record; where that next invocation is a summons to resume the sunset, it writes the record,
is then refused, and no fake records an effect call from the sunset; where, before that summons, the
fixture's env file comes to hold a connection password equal to a description in the sunset's saved
inputs, the sunset's journal shows the disproof record, then the `closed` record, in that order, and
the summons is then refused with that description in no output; a failed gate or a held lock in
that invocation leaves the record unwritten and nothing changed; at no write boundary can both runs
apply an effect, and at none is the key left with
no run that can go on; with two retiring runs on record for the key, the later one is the one read;
a missing protected record, and a keep whose fingerprint no longer matches, each take only their
dependents out of the offer, with the reason in the preview.

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
source as read inside that same state. What of these a provider returned (the inventory, the
source's identity) is held (SEC-4): it rests in a protected record and the completion record refers
to it; the size and the fingerprint are the tool's own measure. Where the whole scope cannot be read
or established, the keep
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
| secret | a provider's token; a database's connection address, and its password; a value of an env file; a key or certificate file; the data in a dump; any value received in a field whose disposition is secret (SEC-4) |
| protected | content the run has not made safe. A provider's value that no ground of SEC-4 has proven: it is held. Content the run read from the owner's files and has not validated: a schedule's command, a launch agent's file, a memory note, the before-image or after-image of a span, the present text of a file |
| safe | content that is safe by where it came from, and no other: the tool's own fixed text, and the fixed words of a declaration; what the tool itself made, counted or measured, and what it built from safe content; the owner's own words typed in this run and validated (SEC-9), and what he wrote in his settings file; content of a file on this machine that the owner or the tool wrote, where a validator the row declares has passed. A provider's value is safe only where a ground of SEC-4 proves it, and what is then kept is the tool's own word or its own copy. Content is no longer safe once its ground is disproved (SEC-12) |

Test on fakes: a canary planted in each secret source and each protected source, and each value a
fake returns during the run in a held or a secret field, appear, by the scan of SEC-11, in no
journal record, manifest, form, output or error; and the same run's forms hold the safe fields
FORM-2 requires, so an implementation that shows nothing fails. After a disproof (SEC-12) of a name
the fixture's owner typed, the forms that a later status summons, a close and a resume render hold
every other safe field FORM-2 requires and, in place of that name, the fixed words that a value is
withheld. The same holds for what is safe as the tool's own: after a disproof of the run's own id,
and in a second pass of a word of the tool's fixed text that the journal holds, those three forms,
and every refusal a later summons can meet before its startup checks pass (RUN-12's test line names
them), hold the fixed words of withholding in the id's and the word's place and that value nowhere.

**SEC-2. Channels.** The hosting token is read in-process by one function, from the environment
variable, else from the hosting tool's own credentials file opened read-only (the owner's ruling,
A2). It is used only in requests the frame itself makes to the provider's fixed host, over TLS,
following no redirect and logging no request, and is then dropped. It is also read at the start of
every invocation for RUN-2's name check, into the register and nowhere else. A database's connection
address is a secret whole, wherever the frame read it: in a file already on this machine, or in a
secret field (SEC-4). No part of it is safe for being that part. Its host, its port, its database
name, its user name and each of its parameters is held unless a ground of SEC-4 proves that part,
and its password is a secret. The whole address, every part of it, travels to the dump tool in the
private password file: built in the run directory, owner-only from its first byte, named to the tool
by a path in its environment (SEC-3), and removed when the tool ends and at the start of the next
invocation if a kill left it. No part of the address is an argument or an environment value. The git
host's tool keeps its own token; the frame never reads it. A protected record that a tool or the
harness adapter needs (a routine's definition to recreate) is
handed over only through a protected input (SEC-3). A held value (SEC-4) goes back to the provider
that issued it in such a request of the frame's own, to that provider's fixed host and to no other,
or through a protected input; it travels no other way.

Test on fakes: the fake host records that the authorization header arrived with the right hash and
that no redirect was followed; a held id reaches the fake host that issued it in the frame's own
request and reaches no other host and no child's argument; with the environment variable absent and
a fixture credentials file present, the same header arrives, and the fixture file system shows that
file opened read-only and left byte-equal; the fake dump tool records the password file's path in
its environment and finds the file owner-only and holding the whole address, with no part of the
address, its host, port, database name, user name or password, in any argument or environment value
it recorded, and the file is gone after the call and after a kill and resume. A lost secret (one
whose record an earlier invocation lost) is then planted as the host and, in a second run, as the
database name of the connection address, once in the fixture's env file and once in a fake's secret
field: in each of the four the part is in no journal record, manifest, form, output or error, and
in no argument or environment value of any fake; and a part that equals a name the owner typed is
shown as his name.

**SEC-3. The child process.** Every child is started by one runner, and only as this table says. A
call to a capability of the harness adapter is declared and bounded the same way, and its answer is
parsed by SEC-4.

| Aspect | Contract |
|---|---|
| command | an argument list built from the row's declared template, filled with validated inputs and with output fields that are safe (SEC-1); never a shell line. A template that puts a held or a secret field (SEC-4) into an argument or an environment value fails when its manifest is built; the lane then reports that tool (ROW-2) |
| environment | built from nothing. It holds the base names `HOME`, `PATH`, `USER`, `LOGNAME`, `LANG` and `LC_ALL` (the last two set to one fixed locale) and `TMPDIR` (set to a private folder in the run directory), and the names the provider module registered for that command, each of one class: fixed (a safe literal); passed (copied from the session, only for a name registered with its reason, never for a name the module lists as carrying a credential); private path (the path of an owner-only file the frame made). Nothing else of the session reaches a child |
| protected input | a slot the declaration names, with the type of protected record it accepts (SEC-6). The frame fills it only with the path of an owner-only file it made from that record, passed in the environment name or the argument position the slot declares. The content is never an argument, never an environment value and never in the CLI's output |
| refusals | the runner refuses: a command with no declaration; an argument on the tool's registered list of debug, verbose and trace flags; any argument or environment value that holds an entry of the secret register in any form SEC-12 names |
| files it makes | a file-creation mask that gives every new file to the owner only; the working directory the row declares |
| input and output | standard input empty; both output streams captured in memory up to a fixed size and handed only to the parser of SEC-4; output over that size is discarded and the result is `malformed` |
| lifetime | its own process group; a time limit from the declaration; at the limit, or when the invocation is ending, the runner ends the group it started, every descendant in it included, and nothing else |

Test on fakes: the fake records its arguments and the names of its environment, and the names equal
the base list plus the registered names; a session debug variable and a session token variable are
absent; a command with no declaration, a trace flag, and a register entry planted in an argument
whole, by component, percent-encoded and in base64 are each refused before the start; four rows,
whose templates put a held field (a provider's own id) into an argument and into a registered
environment value, and a secret field into an argument and into a registered environment value,
each fail the manifest build with the row named and no child started; the same held field declared
as a protected input builds, and reaches the fake as a path to an owner-only file with its content
in no argument or environment value; a file the fake creates is owner-only; a fake that hangs
after starting a child of its own is ended at its limit with that child, and the result is
`timeout`.

**SEC-4. What a provider's result may carry.** A value a provider returns is held unless a ground of
this rule proves it safe (the owner's ruling, A20). The same holds for an answer of the harness
adapter, and for the content of a file that a provider or a provider's tool wrote. No value is safe
because of its shape, and none because a declaration or a provider's document says what its field
is for.

The grounds are three and no other (the owner's rulings, A21). A, a fixed word: the value is one of
a list written in the declaration before the run, and what the tool keeps is its own word from that
list. B, equality: the value equals safe content the invocation already holds (SEC-1): what the
owner typed, what the tool sent in that request, or what the tool itself made, counted, measured or
built; what the tool keeps is its own copy. C, his settings: the value equals a name the owner wrote
in his settings file on this machine; it is the one ground for the account or the team a provider
says the tool acts as. No ground proves a value that holds an entry of the register, or that a
disproof has withheld (SEC-12), whatever it equals.

A provider module declares, for each command, its result fields. Each field has: a name; the place
in the tool's structured answer it is read from; one type from the table below; for each result the
command can give, whether the field is required in it; and one of four dispositions. The frame reads
a field only from its declared place, never by searching the tool's text, and keeps nothing that is
not declared.

| Disposition | What the frame does with the value |
|---|---|
| fixed | ground A. A value on the field's list is kept as the tool's own word; a value off the list makes the result `malformed` |
| equal | ground B or C, against the safe value the declaration names. Where it is equal, the tool keeps its own copy. Where it is not, the tool keeps the fixed fact that it differs, and the value itself is held |
| held | never shown and never written where it can be read. It is kept as a protected record (SEC-6) where a later step needs it, and is otherwise dropped |
| secret | held, and entered in the register (SEC-12) on receipt, before any other field of that result is read. It is the disposition of a credential, a code, a signed or one-time link, and a connection address |

| Type | Its validator, which can refuse a value and never proves one | Dispositions it may have | A value of this type is safe when |
|---|---|---|---|
| exit | an integer | fixed | the declaration lists that exit value and maps it to a kind or an outcome; the number itself is not kept |
| kind | one of `not-found`, `auth`, `conflict`, `terms`, `timeout`, `malformed`, `other` | fixed | it is one of those seven words, and what is kept is the tool's own word |
| state | one of the words the declaration lists for that command | fixed | it is on that list |
| flag | true or false | fixed | it is one of those two words, and what is kept is the tool's own word |
| count | a non-negative integer | equal, held | it equals a number the tool counted or measured itself, or a number safe on record |
| time | a timestamp in one registered form | held | never. A date or a limit in a form is the tool's own clock, its fixed text, or a fact measured beforehand (the catalog's M3) |
| id | the provider's identifier: an alphabet and a length limit the module registers | equal, held, secret | it equals an id that is safe on record. An id a provider made is never that, so it is held |
| name | a key name or a resource name: letters, digits and the punctuation the module registers, with a length limit | fixed, equal, held | it is on the row's fixed list (the required key names, the environment names), or equals a name that is safe by where it came from, or equals a name in his settings |
| hash | a fingerprint in a registered form | equal, held | it equals an address the tool computed itself (a commit it made or read on this machine) |
| address | a link with no user part and no fragment | fixed, equal, held, secret | its whole text is fixed in the declaration, or it equals an address the tool built from safe content. Any other goes to a private file (the owner's ruling, A11) |

An undeclared field is dropped. A declared field that fails its validator, a required field that is
missing, or a fixed field off its list, turns the whole result into kind `malformed` with nothing
kept, but for one thing. A value in a secret field that passed its own validator stays in the tool's
custody whatever becomes of the rest of the result: it is in the register; it is written to its
protected record; the search for it is made; the disproof record is written where the search finds
it; and the receipt is given, all as SEC-12 orders. The operation's result is `malformed` all the
same. A value received in a secret field is searched for in the run's records at once (SEC-12).
Where they hold it, a safe ground is disproved: the run stops, and SEC-12 says what is written first
and what holds in every later invocation. An account or a team that equals no name in his settings
ends the look (RUN-7), and the name the provider reported is shown nowhere. A field that the row
marks as a name form of the project, and that equals none the invocation holds, ends the look as
RUN-2 says.

A held value may do five things and no other: be compared in memory; rest in a protected record,
with the journal, a manifest and a form referring to it (SEC-6); go back to the provider that issued
it (SEC-2); go to a child as a protected input (SEC-3); and be written into a file that SEC-7 names
for it. So each kind of operation still gets what it needs:

| Kind | What it needs from a provider | How it gets it |
|---|---|---|
| create | the new thing's id | held in a protected record; the answer record refers to it (LOG-2); the read of EV-1 (c) and later requests carry it back to its issuer |
| change at a provider | which thing, and its state | the thing is named by a safe name, or by a held id carried back to its issuer; the state is a fixed word |
| check | a value to compare | compared in memory; what is written is the tool's own word, or its own copy of what it expected |
| build | the hosting link file needs the project's ids | built in staging from the held ids and published (SEC-7) |
| keep | the list of what was copied; the source's identity | held in protected records, to which the completion record refers (KEEP-1); the two sides are compared in memory (KEEP-2) |
| owner step | sometimes a name the tool does not hold as safe | the form names a private file (SEC-6) |
| move, owner answer, adopt | nothing from a provider | nothing |

The module also declares, per command, which results are definite: the success that proves the
effect happened, and the kinds that prove it did not; every other result is indefinite.

Test on fakes: a fake issues a fresh value, which it records for the scan, and returns it in a field
of each of the ten types in turn. As an exit, a kind, a state or a flag it is off the list and the
result is `malformed`; as a count that the tool did not count itself, as a time, as an id, as a name
that equals nothing safe, as a hash the tool did not compute, and inside an address, it is held, and
the address goes to a private file; in all ten it is in no journal record, manifest, form, output,
error or argument. The same ten are run with a secret's record missing from an earlier invocation
and the fake returning that lost value, and with the lost value returned in an equal field whose
named safe value is different: it is in no output, and a restore still offers what EV-7 says and
renders its status form. The grounds are each shown to work: a state on its list is shown; a name
equal to the one the tool sent is shown; a count equal to the tool's own count is shown; an account
equal to a name in the fixture settings is shown, and one equal to none ends the look with the
reported name in no output; a name that differs from the one sent yields the fixed fact that it
differs and a private file. A value in a secret field that equals a name on record stops the run
with its disproof on record (SEC-12); in the next invocation, which passes its startup checks, that
name is in no output, and a fake that returns it in an equal field whose named safe value is that
very name finds it held and not shown. A file a fake provider's tool wrote, read back, is held. A
fake that adds a field, mistypes one or omits a required one: the first is dropped, the others yield
`malformed`, and no value from such a result is in the journal; an omitted optional field does not
make the result `malformed`; a result the declaration does not list as definite is treated as
indefinite by OP-6, and a declared definite success as definite. A valid secret beside an invalid
required field: inside an operation a fake returns a result whose secret field holds a valid value
and whose other required field is absent, and in a second pass fails its validator. In both passes
the operation's result is `malformed` and no other field of that result is kept; the journal holds
the receipt-due record and then the receipt, which names the protected record; that record holds
the secret; and the secret is in the register and in no output. In a third pass the fixture's saved
inputs hold that same value: the journal then holds the receipt-due record, the disproof record and
the receipt, in that order, and the run is `stopped` on the disproof.

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
from the content; its type (before-image, after-image, definition, line, values, copy, held field,
secret field); a label the tool wrote from safe content; and a fingerprint keyed with a random value
made for the run and kept only in that folder. Where the owner must have the content (to recreate a
schedule by hand, to judge a merge before he answers, to open a link that was held), the form names
the file's path and says he opens it himself; a file made for him to read before an answer is a
review file, kept in the same folder on the same terms. Where a form must speak of things found at a
provider whose names are held, it says what kind of thing each is and how many there are, by the
tool's own count, and names the file that lists them (the owner's ruling, A21); a name he then types
is his own word and is shown.

Test on fakes: for a schedule whose saved command holds a canary, on a harness with no capability to
recreate it, the owner's step names a file path and a label, and the canary is in no form or output;
a sunset preview over a database whose name at the fake provider equals nothing safe says one
database and names a file, with that name in no form or output, and after the owner types the name
the next preview shows it; the same holds for a review file whose content holds a canary; the
journal's fingerprint of a record is not the plain hash of its content, and two runs give two
different fingerprints for the same content.

**SEC-7. Where a secret or a protected record may rest.** These places and no other, each reached by
the construction this table gives and never through a symbolic link. A place found with wider
permissions than this table gives is a failure.

| Place | What rests there | How it gets there, and its permissions |
|---|---|---|
| the frame's own memory | the hosting token; values on their way to a file; held values in use; the secret register (SEC-12) | read in-process; dropped after use; written nowhere |
| the private password file | the database's connection address, every part of it | a new file built by the frame (SEC-2); owner-only; removed after use |
| the tool's own folder beside the run directories | the value RUN-2 keys a lock's fingerprint with | made once on a machine by the tool; owner-only; shown nowhere and copied nowhere |
| the protected folder of the run directory | protected records, held and secret fields among them; review files; the fingerprint key | new files built by the frame; owner-only; kept with the run |
| staging | a secret-bearing object while it is built | OP-4; until it is published or removed |
| the pulled env file in the working tree | env values | a new file: staged and published by C1; owner-only; ignored by git, proven before every commit (SEC-10) |
| the hosting link file in the working tree | the hosting project's ids, which are held values (SEC-4) | a new file: built in staging from the held ids and published by C1; owner-only; ignored by git, proven before every commit (SEC-10) |
| the sunset folder beside the archived repository | the dump, the saved hosting env values, the memory copy | new files: staged and published by C1 as keeps; owner-only, in an owner-only folder outside every working tree (the owner's ruling, A2) |
| the same sunset folder | a launch agent's file moved there | the file itself, moved by C7; it keeps the permissions it had, inside the owner-only folder |
| the place a thing was taken from, on a restore | a launch agent's file moved back | the file itself, moved by C7 to its original place and no other; it keeps the permissions it had |
| the same | a span put back into its file (EV-6) | a swap, C3, of the file it was taken from and no other; the file keeps the permissions it has, never wider |
| the same | the working memory store copied back from its keep | new files: staged and published by C1 at the original place, which must be empty of anything; with the permissions recorded at the retirement, never wider |
| the same | a routine recreated through the adapter | a protected input (SEC-3) |
| the provider | the token in the authorization header; the password, to the database server; a held value, to the provider that issued it | the authorized transmissions of SEC-2 |

What a tool writes into its own folders is not on this list: it is risk RK1 (RISK-1).

Test on fakes: clean runs of sunrise, sunset and restore produce each artifact this table names (the
env file, the hosting link file, the dump, the saved env values, the memory copy, the protected
records, the moved launch agent's file, the span put back, the store copied back, the keying
value's file), and the canary
and each held value are found only at these places, each reached by the construction and holding the
permissions the table gives; a link planted at any of them fails the operation with nothing written
through it.

**SEC-8. A tool writes a new secret-bearing output only into staging.** The frame checks it there
and publishes it (C1). A tool that cannot be pointed at a staging path, or that has a secret-writing
side effect of its own which cannot be turned off, is not run for that purpose.

Test on fakes: the fake hosting tool's pull writes into a staging path, and the env file appears in
the working tree owner-only and complete; a fake that can only write in place is never started; nor
is a fake whose declaration names a second secret-writing side effect with no way to turn it off.

**SEC-9. Inputs are validated before they are stored.** An input that holds a secret (an address
with a password in it, a description that holds an entry of the secret register) is refused at the
start and is stored nowhere. The names a summons carries are checked first, by RUN-2's name check,
before any lock is taken; until then nothing of a name is written, and after it only the fingerprint
of its key (RUN-2). Every input, those names again among them, is checked by this rule once the
startup checks have passed (SEC-12) and before it is saved. An input found to hold a secret only
later, when that secret first reaches the register, is a safe ground disproved (SEC-12).

Test on fakes: a summons with a password inside an address, and one whose description holds a
register entry, each end refused, and the canary is in no file of the fixture home; a summons with
neither is accepted and its inputs are in the manifest; a summons whose name holds the fixture's
hosting token is refused before a lock exists (RUN-2's test line has the fixture).

**SEC-10. Nothing is committed or pushed unscanned.** Before every commit a check scans, by content,
exactly what will be committed and proves the ignore rule; before a push a check scans every commit
to be pushed. A hit stops the run, names the file and shows nothing.

Test on fakes: a canary in the content about to be committed stops the run before the commit, also
where the working-tree file has since been cleaned; a canary in a working-tree file that is not part
of what will be committed does not; a canary in an earlier commit stops the run before the push; in
each stop the output names the file and holds no canary; with no canary the commit and the push are
made.

**SEC-11. How the secret rules are tested.** A marked canary, built at run time, is planted in every
source SEC-1 names, and every value a fake returns during a run in a held or a secret field, of
whatever type, is recorded by the fake for the scan. The scan covers every file under the fixture
home and the fixture working tree, both output streams, every argument and environment that every
fake recorded for itself and for anything it started, at any depth, and every git object. It looks
for the canary and for each issued value whole, for each of its components, and for the
percent-encoded and base64 forms of both. One found outside a place of SEC-7, or at one with wider
permissions than SEC-7 gives, fails. The fake host records only that an authorization header arrived
and whether its hash is the expected token's; it never stores the header.

Test on fakes: the scan is itself proven: a canary planted in each scanned place, in each form, is
found, including in the recorded arguments of a fake's own child; a canary at a place of SEC-7 with
wider permissions is reported; an issued value planted in a form is found.

**SEC-12. The secret register, the receipt, and the startup guard.** Whether a provider's value may
be shown is SEC-4's to decide, and that never depends on what the tool knows to be a secret. This
rule holds the five things that stand beside SEC-4: a register that is a backstop and no more, a
receipt for every execution that can receive a secret, a lasting record of every safe ground the
tool finds disproved, a read of those records before anything is printed, and the limit on what an
invocation may write before its startup checks have passed. It then says where these apply, place by
place and beginning by beginning.

The register. There is one for an invocation, held in memory and written nowhere. It holds each
secret the invocation has read from a channel of SEC-2, each value it has received in a secret
field (SEC-4), each value a disproof record gives it in the disproof read (below), and the
fingerprint key (SEC-6) of each run directory it has opened. An entry holds the value whole, each
component its source declares (for a connection address: the password, and the user and password
pair), and the percent-encoded and base64 forms of each. Every runner use (SEC-3), every check of a
name or an input (RUN-2,
SEC-9), every proof of a ground (SEC-4) and every write to the journal, a manifest, a form, the
CLI's output or an error consults it. A value that holds an entry goes no further. The runner
refuses the command. The name or the input is refused. No ground proves it. A journal record or a
manifest that would carry it is not written, and the invocation stops with the fixed words that a
value was withheld. A form, the CLI's output and an error carry those fixed words in its place, with
the reference of its disproof record where it has one (SEC-6), and never the value; the form is
still rendered. This holds for every line the tool prints, its own fixed text and a run's id among
them, on every path. Where the fixed words of withholding would themselves hold an entry, nothing is
written in that place. The register does not reach back for a secret: an invocation opens no earlier
record
to learn a secret it has not itself read, and nothing in this frame needs it to, since a value the
register does not know is held by SEC-4 all the same. What an invocation does read back is the
disproof records, as this rule says below.

The receipt. A command whose declaration has a secret field is run only inside an operation, after
that operation's start record. Each execution of it answers for itself: before the child starts,
the journal holds a step record that a receipt is due, naming the operation, the number of this
execution, and the id under which the value will be kept; after the result is parsed, its secret is
in its protected record and the search for it has been made (the next paragraph), a step record
gives the receipt, naming that record, or saying that the result held no such value. None of this
waits on the rest of the result: the record, the search, the disproof record where it is owed and
the receipt are made also where another field turns the result `malformed` (SEC-4). A receipt that
is due and was not given is a secret that may have been received and lost, whatever receipts earlier
executions of the same command have: every status form says so, naming the operation and the
execution, and for EV-7 what needed that value is missing. So a look receives no secret from a
provider. It reads one only from a file already on this machine (SEC-2). Where a look needs a secret
that no such file holds, it does not fetch it: that is a planning stop (RUN-7), and its form gives
the one command the owner runs himself before he summons again. The owner ruled this for the sunset
look and the database's connection address (A23); the words of that stop are the sunset lane's.

A safe ground disproved. Each time a value enters the register, the invocation searches for it in
what its run has on record as safe: the saved inputs, every manifest and the journal. It does so at
once, before it uses the value for anything else. For a value it reads at its start, as the name
check reads the hosting token before a run directory is open, it does so in the disproof read, and
what follows a find there is said below. Where the records hold a value that arrives later, a safe
ground is disproved (SEC-1), and the invocation does two things before anything else. First, in a
run that has its go, it appends a disproof record to the journal (LOG-1). The record says where the
value rests in the run directory and holds nothing of the value: for a value from a secret field,
the protected record that holds it; for a channel secret, of which the tool keeps no copy (the
owner's ruling, A2), the recorded content that holds it, by its place and the span within it. Then
the invocation ends: `stopped` in a run
that has its go; `refused` before a first go, where there is no journal to hold a disproof record.
That is so for a look, and for the invocation that was to record his go on a manifest an earlier
invocation made: it records no go, writes no journal record and opens no run. In both a refusal form
is rendered, with the fixed words in the value's place, and the next summons starts a new look
(RUN-12). That look reads the same channel and meets the same secret; where the channel no longer
holds it, that is RK6. The reason kind is a safe ground disproved, and its line is the lane's to
give (FORM-2). For a command with a secret field, the receipt is given only after the search and,
where the search found the value, after the disproof record.

What holds from then on. No disproof record is removed or ended, by the tool or by a word. Every
invocation that continues the run makes the disproof read, and so does the invocation that is to
record a go on a manifest an earlier invocation made. It is the last of the startup checks, in
RUN-1's third step, after RUN-4's checks, and it writes nothing. It reads each disproof record of
the run's journal, reads the value from where the record says it rests, and enters it in the
register. It then makes the search of the paragraph above for three more kinds of value: each one
the register already holds, which is the hosting token read for the name check; each secret that
the manifest shows the run reads from a file on this machine, which is the connection address, read
again there in-process, where the file still holds one; and, for a receipt that is due and not
given, the value in the protected record its due record names, where that record is present. What
it finds stays in the register. In a run that has its go, the disproof record owed for it, and then
that receipt, are the invocation's first journal records once the startup checks have passed, in the
order of first records below, and the invocation goes on as its kind of summons has it, under the
register. Before a first go it ends
`refused`, as the paragraph above says. A disproof record whose value cannot be read where the
record says is a failure of RUN-4's checks. From the disproof read on, the register does for each
such value all that its paragraph says. A status
summons, a close and a resume each render their form with the fixed words in the value's place. No
ground proves a value equal to it. An operation whose command, record or form line would carry it is
not started, and the run ends `stopped`; the ways on are a re-plan in which the owner changes the
input or drops the layer (RUN-11), a close (RUN-13) and, for a retirement, a restore over what is
finished (EV-7). Nothing already written is taken back: the forms rendered before the disproof, and
whatever the run's finished operations published, keep what they held, and the status form's lines
for those operations say where the run wrote.

The order of first records. Once its startup checks have passed, an invocation that continues a run
writes its first journal records in this order, and no rule gives another. First, in the run's own
journal, each disproof record the disproof read owes. Second, there too, each receipt it owes.
Third, where EV-7's handover owes it, the retirement's `closed` record, in the retirement's journal,
whichever of the two runs the invocation continues. Fourth, the record of what it was summoned for:
his word to go on, his answer, or his close. Then the records of whatever it does. So EV-7's
`closed` record follows the disproof records and the receipts and comes before every other record. A
close record (RUN-13) is one more record after all three kinds and never stands in the place of one.
An invocation that is refused once the third is written, as a resume of a retirement that a restore
has closed is, writes nothing more.

Another run's journal. An invocation that reads the journal or the records of a run other than its
own (RUN-5, EV-7) first makes RUN-4's checks on that run directory and then that run's disproof
read; a failure of either is a failed read (RUN-7). Where it reads several such runs, it does this
for every one of them before it uses, renders or copies anything of any of them. From then on,
whatever it takes from the records of any of those runs that holds a value any of those disproof
reads gave is held (SEC-4): it is no ground, it is rendered only as the fixed words, and it enters
no new record and no command. A restore plans an operation that would need such content
`not applicable`, with that reason, and still offers the rest (the owner's ruling, A26; EV-7). Those
values are used for nothing else and do not enter the reading run's register.

What another run does not know. A disproof is known only where a journal holds its record; the tool
keeps no memory of one across runs (the owner's ruling, A26). Take a run that closed before the
catch and holds in its journal a name the owner typed; a later run under the same key that received
that value in a secret field; and a third run whose first look reads both journals. Where the later
run's own records held the name, its journal holds a disproof record, and the third run holds the
name wherever it takes it from either run's records. Where they did not, no journal holds a disproof
record: the third run does not know, takes the name from the first run's journal as safe content,
and may render it and copy it into its own manifest. In both, what the owner types in the third run
is his own word in that run (SEC-1) and is shown, and it is searched for again whenever a secret
reaches that run's register. The same holds for anything else that the first run's records hold as
safe by SEC-1, whatever it came from. This is RK7, which the owner accepted for the whole of what a
run holds as safe (A30; RISK-1). RK7 reaches no further than that: a value a run does not hold as
safe is held back by SEC-4; a secret lost in the instant a provider hands it over is RK8; and a
channel secret replaced before its channel was read is RK6.

The withheld read, and what a refusal prints. A value a run has caught is hidden by every later
invocation on every path, a refusal's included, and whatever the value is: a name, a run's own id,
or a part of the tool's own fixed text. So the first act of the gate, before the invocation prints
anything, is the withheld read. It reads the record of every lock and the record of open runs. For
each run that either of them holds, a run on record, it makes RUN-4's checks on that run directory
and, whatever they find, reads the disproof records of that journal as far as they can be read, and
each value from where its record says it rests. A check that fails there stops nothing at the gate,
whichever run's directory it is: it bears only on whether that run's id may be printed, as this
paragraph goes on to say. The stop RUN-4 orders is made in RUN-1's third step, by an invocation that
continues that run, and by no other. The withheld read holds those values for printing only: they
are not entries of the register, and no check of a name or of an input sees them. It reads nothing
outside the tool's own folder and those run directories, and it writes nothing. Until the startup
checks have passed, every line the invocation prints is passed against those values, as the
register's paragraph passes a line against an entry. A line of fixed text that holds one of them is
not printed, and the fixed words of withholding stand in its place. A run's id is printed only where
the disproof records of that run were read whole and the id holds none of those values. That read is
whole where two things hold: the chain of that journal (LOG-1), which is one of RUN-4's two checks,
holds from its first record to its last; and the value of every disproof record in the journal was
read from where its record says it rests. RUN-4's other check, that the directory is owner-only,
does not enter into it. Otherwise the fixed words stand in its place, with the name of the file
whose record holds that id, which is a lock's file or the record of open runs, and the owner opens
that file himself to read it. Where a
disproof record of a run on record, or its value, cannot be read, the tool cannot tell what that run
has caught: that run's id is printed on no path, and what else is printed is passed against the
values the read did give. A disproof is a record in a run directory, and like every proof of this
frame it holds only while nothing but the run changes that directory (RUN-4). Once the startup
checks have passed, the register holds what the invocation's own run's disproof read gave, and the
values of the withheld read are used only to decide, in the same way, whether another run's id may
be printed. The early paths are these, and each prints under this paragraph: a
failed check of the gate, the keying value's among them (RUN-2); a name that fails its check; a held
lock, the first key's or a later key's; a new summons met by an open run, at the early look or at
the second (RUN-3); and a stop by RUN-4's checks on the run directory that the invocation itself
continues, a disproof record of that run that cannot be read among them.

Before the startup checks pass. The startup checks are RUN-1's first two steps (the gate; the name
check, the locks and the looks for an open run), RUN-4's checks on the run directory the invocation
continues or is to record a go for, and that run's disproof read. Until they have passed, an
invocation uses no runner, parses no result, checks no input but the names, by RUN-2's name check,
and writes nothing but these: the tool's own fixed text and the id of a run, which the tool itself
made, each only as the withheld read lets it be printed; in a lock's record and file name, the
fingerprint of a key (RUN-2); and, once on a machine, the keying value (SEC-7). It writes nothing
that it read from a journal, a manifest or any other record, whatever that content was when it was
recorded.

The places a value can go. Thirteen are this rule's and SEC-4's to name; four stay with the rule
that already holds them. A place that is not in this table is not a place the tool may write a
value.

| Place | What may go there | Held by |
|---|---|---|
| the CLI's output | safe content (SEC-1) and references to protected records (SEC-6); nothing held and nothing secret; in place of a value a disproof has withheld, the fixed words, the tool's own fixed text and a run's id being printed only as the register and the withheld read let them be | this rule |
| a preview | the same | this rule; FORM-1 |
| a status form | the same | this rule; FORM-1 |
| a refusal form | the same; before the startup checks pass there is none (RUN-12) | this rule; RUN-12 |
| a manifest | the same | this rule; RUN-8 |
| the journal | the same | this rule; LOG-1 |
| the record of open runs | the fingerprints of project keys (RUN-2) and run ids; no name, no key and no provider's value | this rule; RUN-3 |
| a lock's own record | the fingerprint of a project key, which is also the lock's file name, and the id of the run that holds it; no name and no key | this rule; RUN-2 |
| a command of the look | arguments and environment of safe content only; a held value by a protected input or not at all | this rule; SEC-3 |
| a command of an operation | the same | this rule; SEC-3 |
| a command that reads for one of his steps | the same | this rule; SEC-3, OP-9 |
| a file the tool publishes outside the run directory | a secret, a held value or protected content only at a place SEC-7 names for it, by the construction SEC-7 gives, and at every one of those: the pulled env file, the hosting link file, each keep in the sunset folder (the dump, the saved hosting env values, the memory copy, a moved launch agent's file), and each thing a restore puts back at its place. Every other file the tool publishes holds safe content only | this rule; SEC-7 |
| the cue | no value: a fixed sound and a fixed line | this rule |
| an input saved for the run | what SEC-9 has passed | SEC-9 |
| a protected record | held, secret and protected content | SEC-6, SEC-7 |
| a review file | the same | SEC-6, SEC-7 |
| staging | an object while it is built | OP-4, SEC-7, SEC-8 |

The ways an invocation can begin. There are twelve. Every one of them makes the common startup
reads, as far as it gets. All of them are of this machine, none is of a provider, and none uses a
runner. They are: what the gate reads, which is the withheld read's reads (every lock's record, the
record of open runs and, in the directory of each run on record, what RUN-4's checks read, the
journal's disproof records and what each points to) and what its checks read, the keying value's
file among it; the hosting token's channel, for the name check; the record of each lock it takes or
meets; the record of open runs, for its looks for an open run; for
a new summons and a re-plan, the alias reads; and, for a line that continues a run or is to record a
go, its run directory for RUN-4's checks and, in the disproof read, the journal's disproof records,
the record or the content each points to, and each file the manifest shows the run reads a secret
from. The third cell of each line says what that line reads beyond these: of a provider, through a
runner, of the project, or of another run. For the two refusal lines it says instead how far into
the common reads each path gets. "Fixed text" is all that the paragraph on the startup checks
allows: the fixed text and a run's id, each as the withheld read lets it be printed, a key's
fingerprint in a lock, and once the keying value.

| How the invocation begins | Allowed by | What it reads at its start | Before the startup checks pass it writes | Once they have passed it may write |
|---|---|---|---|---|
| a first look of a sunrise or a sunset | RUN-1, RUN-5 | the whole look; within it, the journals of the key's earlier runs, each after that run's disproof read; a secret only from a file on this machine, and where none holds it the look ends as a planning stop (A23) | fixed text | its forms, the CLI's output and its manifest; no journal before a go (RUN-12) |
| a first look of a restore | RUN-1, RUN-5, EV-7 | the whole look; of the retiring run it reads the journal and the records EV-7 needs, after that run's disproof read | fixed text | the same |
| the invocation that records a go and runs operations | RUN-9 | where the look was made by an earlier invocation, what RUN-10 (b) compares and OP-9's reads; otherwise nothing further | fixed text | the journal, its forms and the CLI's output |
| a resume on his current word | RUN-10 | what RUN-10 (b) compares (each provider's identity among it) and OP-9's reads | fixed text | the same |
| a summons with no word or a stale one, the first after a kill included: it renders status and ends | RUN-10 | for each provider that has a waiting read-back step, its identity read and that step's read (OP-9); no planning read | fixed text | the journal, the status form and the CLI's output |
| a resume that finds its context changed | RUN-10 (b) | what RUN-10 (b) compares, and then nothing: it ends asking for a re-plan | fixed text | the status form and the CLI's output |
| a re-plan | RUN-11 | the whole look | fixed text | the journal, its forms, the CLI's output and the new manifest |
| a close; a summons to resume a run that is closed | RUN-13 | nothing beyond the common startup reads: a close makes no provider read and uses no runner, and the resume is refused before any | fixed text | for a close, the disproof records and receipts it owes and then the one close record, in the order of first records, the form and the CLI's output; for the refused resume, a refusal (RUN-12) |
| a start whose first act is a read or an answer for one of his steps | OP-9, RUN-10 | as the resume or the status-only line it is: the provider's identity read, then that step's read | fixed text | as that line |
| a summons refused at the gate, at the name check, or at a held lock, the first key's or a later key's | RUN-1, RUN-2, RUN-12 | nothing of a provider. Of this machine: at the gate, the withheld read's reads and what its checks read; at the name check, the token's channel; at a first lock, that lock's record; at a later lock, also the early look's read of the record of open runs and the alias reads, and no other thing of the project | fixed text and, at the keying value's check and at a lock, run ids, each as the withheld read lets it be printed; nothing is created | nothing: it does not pass them |
| a new summons refused because a run is open | RUN-3, RUN-12 | nothing of a provider. Of this machine: at the early look, the record of open runs and nothing of the project; at the second look, also the alias reads, and no other thing of the project | fixed text and the open run's id, each as the withheld read lets it be printed; nothing is created | nothing: it does not pass them |
| an invocation that finds a restore's go and no closing record on the retirement (the handover's repair) | EV-7 | before the repair, nothing beyond the common startup reads and, to find the closing record missing, the journal of the other run of the pair, after RUN-4's checks on that run directory | fixed text | in the order of first records: the disproof records and the receipts it owes in its own journal, then the one closing record in the retirement's journal; then it is refused or goes on as its own line says |

In any line that continues a run, a failure of RUN-4's checks stops the invocation with the fixed
text, printed as the withheld read lets it be, and nothing else written. The rules that let an
invocation begin or end are RUN-1 to RUN-13,
OP-9 and EV-7; these twelve lines are every beginning they allow. Three things this rule does not
reach, and says so: a secret the frame never reads into memory (a value inside a file a tool wrote
into staging), which SEC-11's scan is what checks; a secret that had left its channel before this
invocation read that channel (a token since replaced); and the death of an invocation in the
instant between a provider's handing it a secret and its first record of that secret. The second is
RK6, which the owner accepted (A18; RISK-1), and by his word the tool keeps no copy of a channel
secret to close it. Such a value repeated in a provider's answer is held by SEC-4 like any other;
RK6 now covers only the same value typed by the owner or found in a file on this machine, which the
register does not know. The third is RK8, which the owner accepted, and by his later ruling for
anything the run holds as safe (A26, A32; RISK-1). The receipt stays due, every status form of that
run says so, the run goes on, and the tool cannot tell whether that lost value is one that run's
records hold as safe. RK8 reaches no further: a value the run does not hold as safe is held back by
SEC-4, and a secret whose protected record was written before the death is found by the next
disproof read. A provider that repeats the lost value finds it held by SEC-4 like any other. A
channel secret has no such instant left open: the disproof read of every later invocation reads its
channel again and makes the search, and a channel that by then holds another secret is RK6.

Test on fakes: the receipt. A command with a secret field is killed after its receipt-due record and
before its receipt, once on its first execution, and once on a second execution of the same command
after the first had its receipt and the fake then issued a different value. In both, the next status
form names that operation and that execution; and the lost value, returned by the fake through a
field of each of SEC-4's ten types and asked for back in an argument, is in no journal record,
manifest, form, CLI output, error or argument. A row that puts a command with a secret field into a
look fails its manifest build. A sunset fixture with a database and a hosting project, and no env
file on the machine, ends its first look `refused` before any preview, with the lane's one command
in the refusal form and no call of a command with a secret field recorded by any fake; the same
fixture with the env file present reads the connection from it and reaches its preview.
The startup guard. For each of the twelve lines a failure is planted before the startup checks pass,
each that the line can meet: a failed gate, a name that fails its check, a held first lock, a held
later lock, an open run found at the early look and one found at the second, a run directory with
wider permissions, a journal with a broken chain, a disproof record whose value cannot be read. The
fixture's journal and manifest hold a name recorded as safe, and a later disproof record of it. Each
ends with output that is the tool's fixed text and at most run ids, with that name in no output, and
with no status form rendered from the records. The early paths. A fixture run has caught, with its
disproof on record, its own id, and in a second pass a word of the tool's fixed refusal text that
its journal holds; RUN-2's test line drives it to the keying value's refusal and RUN-12's to every
other early path. On each the fake file system shows the withheld read made before the first byte of
output, and the caught id and the caught word in no output. That run's disproof record is then cut
out of its journal, from between two records that stay, so that the chain breaks there: its id is
still in no output on any early path, and the name of the file whose record holds it stands in its
place. Another run's directory: a second run on record, which has caught nothing, has a file in its
directory given wider permissions, and in another pass has a record cut from the middle of its
journal. In neither pass does that failed check stop a summons for another project: with the keying
value's file in place that summons passes the gate and goes on; with the keying value's file
removed, the gate's refusal lists the second run by its id in the first pass, and by the fixed words
and the file's name in the second. A summons that continues the second run is stopped by RUN-4's
checks in both passes, in RUN-1's third step. RK8's case. A row's validator passes a line of a file
on the
fixture machine as safe, and the manifest holds that line. A fake returns the line in a secret field
and the invocation is killed after the receipt-due record and before the protected record is
written. The next status form says that a secret may have been received and lost, naming the
operation and the execution; the line is still shown; and the next resume goes on. With the kill
moved to after the protected record is written, the same status form withholds the line; and in
neither pass is a value the run does not hold as safe in any output. The order of first records. A
sunset has a restore's go on record and no `closed` record; it was killed between a protected record
and its disproof record; and its env file then comes to hold a password equal to a saved
description. The next summons to resume the sunset writes two disproof records, then the receipt,
then the `closed` record, and no other record, and is then refused; a close of an open run that owes
a disproof record and a receipt writes those two and then the close record. The table's reads. For
each of the twelve lines
the fakes record exactly the provider calls and the runner uses its third cell names and no other,
and the fixture file system records, of this machine, the common startup reads that line reaches,
the reads its third cell names, and no other. So there is no provider call and no runner use for a
close, for a refusal at the gate, at the name check or at a lock, and for a new summons met by an
open run. A close of a sunset records these reads and no other: the gate's, its withheld read of
every run on record among them, the token's channel, its
locks' records, the record of open runs, its run directory, its disproof records with what each
points to, and the env file its manifest shows the connection is read from. A refusal at a first
lock or at the early look records no read of the project; one at a later lock or at the second look
records the alias reads and no other read of the project; a status-only summons records, beyond the
common reads, the identity read and the waiting step's read, and no planning read. The go: a look
saves a description, and the fixture's hosting token is then set to that same text. The invocation
given his go finds it in its disproof read, records no go, writes no journal record, opens no run
and ends `refused`, with the fixed words in its refusal form and the text in no output; the next
summons starts a new look.
The disproof. A fixture run has its go; its saved inputs, its manifest and its journal hold a name
the owner typed and a path the tool built from it. A fake then returns that name in a secret field.
The journal then holds, in this order, the receipt-due record, the disproof record, which refers to
the protected record and holds nothing of the name, and the receipt; and the run is `stopped`. Each
of these then passes its startup checks: a status summons; a resume on his current word; a re-plan;
a close; once the run is closed, the first look of a later run under the same key; and, in a second
fixture that is a sunset, the first look of a restore over it. In every one the name is in no
output, form, error, new record or argument, alone or inside the path, with one exception: the later
run and the restore, where the owner types the name anew, each show that word and what they build
from it as their own safe content, and withhold only what they take from the other run's records.
Each form is rendered, with the fixed words and the record's reference in the name's
place and with every other line FORM-2 requires. A fake that returns the name in an equal field
named for it finds it held. The resume starts no command whose argument holds the name and ends
`stopped`. The re-plan ends `stopped` with the manifest in force byte-equal. The restore plans the
reverses whose inputs hold the name `not applicable`, with that reason, and offers the rest. The
same six are run after a kill between the protected record and the disproof record: each withholds
the name all the same, and the first of them that continues the run writes the disproof record and
then the receipt as its first journal records. With the protected record removed, each that
continues the run ends as a failure of RUN-4's checks, with fixed text, and each that reads it from
another run ends its look as a failed read. A channel secret: the fixture's saved description holds
the password of the connection address in the fixture's env file; when an operation reads the
connection, the disproof record names the description and the span, no file of the fixture home
holds a new copy of the password, and the same six withhold it. The hosting token: a fixture run
whose saved description holds the fixture's current token renders its next status form with the
fixed words in the token's place and then holds a disproof record. A kill between the read of the
connection address and its disproof record: the next status summons and the next close each read
the env file again in the disproof read, withhold the password, and write the disproof record.
Three runs under one key: the first, closed, holds in its journal a name the owner typed; the
second receives that name in a secret field. Where the second's records hold the name, its journal
holds a disproof record, and the third run's first look holds the name wherever the first's or the
second's records give it. Where they do not, no journal holds one, and the third run's look takes
the name from the first's journal as safe content. In both the third run shows the name where the
owner types it anew.
The register. A channel secret planted in an argument, in an input and in a name, and directly on
its way to each of the journal, a manifest, a form, the CLI's output and an error, is refused, not
written, or replaced by the fixed words, with no part of it in any output; the same for a value a
fake returns in a secret field and then asks for back. The places. A held value driven toward each
of the twelve places where the table allows none reaches none of them. At the thirteenth, the files
published outside the run directory, a sunrise fixture publishes the hosting link file, holding the
held ids, and the pulled env file; a sunset fixture with hosting values, a database, a memory store
and a launch agent publishes the saved env values, the dump, the memory copy and the moved file; and
a restore puts back the moved file, a span and the store. Each is at its place of SEC-7 with the
permissions SEC-7 gives, and the scan of SEC-11 finds held values and secrets at those places and in
no other published file. The record of open runs and a lock's own record hold only fingerprints and
run ids; the cue's fake records the same fixed call in every run. No fake file system records a read
of the protected folder of a run other than the one continued, but in the reads RUN-5 and EV-7
order, and the register's content is in no file of the fixture home outside the places of SEC-7.

### 3.8 Forms

**FORM-1. Where a form's text comes from.** A form is a file in the run directory, named in the
CLI's output and shown by the adapter. Its text comes from four sources only: v1's fixed text for
that form, the lines of FORM-2, text the tool wrote from safe content (SEC-1), and the owner's own
words. A value is in a form because it is safe by SEC-1, never because of the field it came in.

Test on fakes: with a canary in every protected source and in every tool's output, each form of each
run is rendered and holds no canary, and holds each line FORM-2 requires for the statuses that
occurred, with the parts FORM-2 names; a form template that reads a file's text directly fails its
build test.

**FORM-2. The lines this frame fixes, in every form that lists operations.** A preview, a status
form, a summary and a last record can each show every line below, and a lane's list of form changes
includes them. This table does not hold a line for every status, nor every reason, that the rules of
this frame name. A line it lacks is for the lane's list of form changes to give, and what such a
line says is not this frame's to say (the owner's ruling, A9; ROW-3). A status that occurs in a run
and has a line neither in this table nor in the lane's list of form changes fails the build of every
form that lists operations.

| For | The line says |
|---|---|
| `done` | what was done |
| `already so` | found already so; a restore will not reverse it |
| `not proven` | started by this run and not proven finished by it; a restore will ask before reversing it |
| `adopted` | taken as the project's on the owner's input, with its identity: shown where it is safe by SEC-1, as where he typed it, and named by its protected record where it is held (SEC-4) |
| `waiting` | the exact step, its mode, and how the tool will know it is done |
| `done by owner` | done by him, and whether a read checked it |
| `left` | left, by his word |
| `held` | not run, with its reason as ORD-1 records it: the need, and the status of the operation it waited on |
| `refused`, `not needed` | which branch was taken |
| `not applicable` | the reason: a flag, the project type, a layer the project lacks, not available on this harness, or cannot be tied to its copy, with the step he can take himself |
| `unavailable` | the check could not be made on this harness |
| an outstanding create | a create was sent and no answer came; what he can check; the ways on |
| a stop | the reason kind; the operation, where the stop is in one; the command he can run, where a command failed (SEC-5); for a "need unmet" stop, the need and the provider's status (ORD-1); the ways on (RUN-12) |
| a protected record | its label and the path of its file |

Test on fakes: a run driven through every status in this table renders every form with the matching
line, and each line holds the parts its row names (for `waiting` the step and the mode, for
`done by owner` whether a read checked it, for `held` the need and the status waited on, for
`not applicable` the reason, for a stop the reason kind and the ways on, for a protected record the
label and the path); a form template that lacks one of these lines, or renders one without a part
its row names, fails its build test; a run in which a status occurs that this table has no line for
renders its forms where the lane's list of form changes gives that status a line, and fails each
such form's build where neither has one.

**FORM-3. A restore has forms of its own.** A restore has a preview, a status form, a summary, and
its entry in the project's record (KEEP-5). They are forms under FORM-1 and FORM-2, and are not
changes to a v1 form.

Test on fakes: a restore run renders each of the four; its preview lists exactly the reverses EV-5
offers and, with its reason, each operation not offered; each of the four holds, for every status
that occurred in that restore, the line FORM-2 or the lane's list of form changes gives it.

### 3.9 What a row states

**ROW-1. A row states all of this, or the manifest is not built from it.** Every row of every kind
carries every entry of this table. For its kind each entry is one of three things. R: required, and
the row states it. F: forbidden, and the row writes the word `none`. O: it applies to some rows of
the kind, by the condition the entry gives; the row states it where it applies and writes `none`
where it does not. An entry is never left out and never left empty. Two things are not a row's to
state, and are F in this table for that reason alone. The mode of an owner answer is `answer`, by
its kind; the manifest fixes it from the kind, as OP-9 requires, and the row's mode entry is `none`.
The planning test of a check, an owner step or an owner answer is the generic one of RUN-7, that its
needs can be met (ORD-2); it is the one planning test RUN-6 has the look make for such a candidate,
it is the frame's and the same for every such row, and the row's planning-test entry is `none`.

| Entry | check | build | keep | create | change | move | owner step | owner answer | adopt | Used by |
|---|---|---|---|---|---|---|---|---|---|---|
| id, kind and phase | R | R | R | R | R | R | R | R | R | OP-2, ORD-4 |
| the thing it acts on or reads: its role, how its identity is read, and its tracked state; or the output field it refers to | R | R | R | R | R | R | R | F | R | RUN-6, OP-5, OP-8, EV-3 |
| its own planning test: what the look reads of its place or its thing | F: the generic test of RUN-7 | R | R | R | R | R | F: the generic test | F: the generic test | R | RUN-6, RUN-7 |
| before-test | F | R | R | R | R | R | F | F | F | OP-5 |
| after-test | F | R | R | R | R | R | O: in read-back mode | F | F | OP-5, OP-9 |
| construction; for C2 and C5 the document cited, and for C5 each condition the refusal covers; for C3, C6 and C7, and for a shortcut's add or put-back, each accepted risk it is carried under | F | R | R | R | R | R | F | F | F | OP-3, RISK-1, RISK-2 |
| each declared command: the argument template, the registered environment names, any protected input, the time limit; each result field with its place, type, disposition, the fixed list or the safe value it is compared with, and whether it is required; the definite results; the alternative results | O: where it runs a tool or calls the adapter | O: the same | O: the same | R | O: the same; always for C4, C5 and C6 | O: the same | O: where its read runs a tool or calls the adapter | F | F | OP-1, SEC-3, SEC-4, ORD-3 |
| each command that can change a repository | F | O: where there is one | O: the same | O: the same | O: the same | O: the same | F | F | F | OP-11 |
| after-check | F | R | R | R | R | R | F | F | F | OP-6, EV-1 |
| the output it provides and that output's fields | R | R | R | R | R | R | R | R | R | ORD-1 |
| each need, with its level, the answer value it names where the level is answered, and its treatment when nothing provides it | O: where it has a need | O | O | O | O | O | O | O | O | ORD-1, ORD-2 |
| condition | O: where it has one | O | O | O | O | O | O | O | O | ORD-3 |
| how a lost answer can be resolved, with the provider's document, or "by dropping the layer only" | F | F | F | R | F | F | F | F | F | OP-7 |
| way back: the reverse, written as a row of its own kind that this frame allows, or `none` with the reason | F | F | F | F | R | R | R | F | F | EV-4 |
| the inputs its reverse needs, and how each is read and saved | F | F | F | F | O: where a way back is declared | O: the same | O: the same | F | F | LOG-2, OP-9 |
| for a span, its placement and whether the file is ordered | F | F | F | F | O: where the thing is a span and a way back is declared | F | F | F | F | EV-6 |
| mode: read back, or on his word | F | F | F | F | F | F | R | F: `answer`, by its kind | F | OP-9 |
| the safe content its step or its question is built from | F | F | F | F | F | F | R | R | F | OP-9 |
| the answers it allows | F | F | F | F | F | F | F | R | F | OP-9 |
| review file | F | F | F | F | F | F | O: where he must read content first | O: the same | F | SEC-6 |
| how the owner names the thing | F | F | F | F | F | F | F | F | R | OP-10 |
| its scope, how the inventory and the copy share one state, and its content checks | F | F | R | F | F | F | F | F | F | KEEP-1 |
| the keeps it requires | F | F | F | F | O: where it retires a thing | O: the same | O: the same | F | F | KEEP-2, KEEP-3 |
| the class of every content it reads, stores or shows; any validator that makes content of a file on this machine safe (SEC-1), none being able to make a provider's value safe; each resting place it uses | R | R | R | R | R | R | R | R | R | SEC-1, SEC-7 |
| its lines in each form | R | R | R | R | R | R | R | R | R | FORM-2 |

Test on fakes: for each of the nine kinds, a row that states every R entry, writes `none` for every
F entry, and states or writes `none` for each O entry as its condition says, builds; the same row
fails the manifest build, naming the entry, with an R entry written `none`, with an F entry stated,
with an O entry written `none` where its condition holds or stated where it does not, and with any
entry left out or left empty; and a row whose entry is stated but not allowed (a construction OP-2
does not give its kind, an accepted risk that does not cover its construction, a level ORD-1 does
not have, a disposition SEC-4 does not give its type, a reverse EV-4 does not allow) fails the same
way; an owner-answer row builds with its mode entry `none`, and its entry in the manifest holds the
mode `answer`; a check row and each owner row build with the planning-test entry `none`, and the
look plans each by RUN-7's generic test, `in` where its needs can be met.

**ROW-2. A step becomes the owner's only by his word.** Where a lane finds a tool that cannot be
split into single effects (OP-1), whose repository writes cannot be listed (OP-11), that cannot be
pointed at staging (SEC-8), or that takes a held value only as an argument (SEC-3), the lane reports
it before its rows are read, and the step is put to the owner before it becomes his (the owner's
ruling, A6). A row that stands an owner step in for such an effect cites his ruling on it.

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

**RISK-1. The accepted risks stand as the catalog's Part 6 states them.** The owner accepted eight
risks and one assumption (the contract's section 18, A4, A6, A18, A26, A30 and A32): RK1; RK2, which
by his word covers every swap, C3; RK3, for the four rows it names; RK4, for a move, C7; RK5, for a
shortcut's name being free, in the add and in the put-back; RK6, for a channel secret replaced
before an invocation read its channel (SEC-12); RK7, for a live secret among whatever a run holds as
safe, across runs (SEC-12); RK8, for a death in the instant a provider hands the tool a secret
(SEC-12); and the run directory's assumption (RUN-4). Their wording is in the catalog's Part 6 and
is not restated here. This frame removes none of them and accepts none itself. An operation carried
under RK2, RK3, RK4 or RK5 is marked so in the journal, once for each of those risks it is carried
under. RK1, RK6, RK7 and RK8 belong to no one operation, and no mark is recorded for any of them.
Where RK8's instant has passed, the journal already shows a receipt due and not given (SEC-12); that
is the record of what happened, and no mark of a risk.

Test on fakes: every operation built by C3, C6 or C7 carries the mark of its risk; a shortcut's add
and its put-back carry RK5's mark beside RK2's; each mark is recorded exactly once for its operation
and its risk, also after a kill and a resume; no other operation carries a mark, and no record
carries a mark for RK1, RK6, RK7 or RK8, an operation with a receipt due and not given and a run
that holds a disproof record among them. What RK8 covers is tested by its case in SEC-12's test
line, and by nothing wider: after a death between a provider's handing over a secret and the tool's
first record of it, the receipt is due and not given, the status form says a secret may have been
received and lost, the run goes on, and the one thing still shown that the secret may equal is
content that run held as safe before the death; with the protected record written before the death,
that content is withheld.

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
| after the answer record, before the completion record | the answer record in the journal, referring to the id from the call's own answer, which is held in a protected record | `landed`: the after-check by that id, under the expected account, then completion on ground (c): `done` | LOG-2, OP-5, OP-6, EV-1 |
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
| after the start record, before the rename | the recorded object at the source; nothing at the target | `not landed`, the before pairing: a new start record; the rename again | OP-5, OP-6 |
| after the rename, before the completion record | nothing at the source; the recorded object at the target | `landed`, the after pairing: `not proven`; the run goes on, later operations reading the new path from this record; a restore asks before reversing it | OP-6, EV-2, EV-5 |
| variant: killed before the rename, and the owner then moves the folder by hand | exactly the same as the line above | the same: `not proven`. The run does not claim the move | EV-1 |
| after the completion record | `done`, with its way back recorded | not probed | EV-3, EV-4 |
| variant: another folder is put at the source between the identity read and the rename | the target holds a folder with another identity | the read after the rename differs: stop with both places named and no completion recorded; on resume the probe answers `foreign` | OP-3, RISK-1 |
| variant: both places hold a folder, or neither does, or either holds a folder of another identity | neither pairing | `foreign`: stop, naming both places | OP-5 |

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
