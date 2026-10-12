# E16 operation catalog: sunrise, sunset and restore, one row per operation

Written 2026-10-12 by the control room on the owner's word ("a", to "one table, one source"),
after the outside reviewer's second design read found the first design's gaps returning. **This
document is the single source for how the lifecycle code works.** The lane contract
(`2026-10-11-stations-e16.md`) holds the owner's rulings and points here; it restates no mechanic.
The three design pages of 2026-10-11 are withdrawn. Where this document and anything else
disagree about a mechanic, this document is right and the other text is a defect.
**Status: not yet read by the outside reviewer.**

How to read it. Part 1 is the executor: thirteen rules, each stated once. Part 2 is the evidence a
run may use to say "I did this". Part 3 is how a secret travels. Part 4 is the catalog: every
operation of sunrise, sunset and restore as one row with the same columns. Part 5 is the forms.
Part 6 is what is measured later and what risk is left. A builder builds Parts 1 to 3 as the frame
(slice 1) and the rows of Part 4 as the lanes (slices 2 to 4).

## Part 1. The executor's rules

| # | Rule |
|---|---|
| X1 | **One run at a time per project.** A run holds an exclusive lock on the project's name and on its run directory from before its first probe until it ends. A second run stops at once and names the first. |
| X2 | **The run directory** is a private folder in the owner's home directory, outside every repository, one folder per run, readable by the owner only; finished runs are kept (ruled, A2). It holds the validated inputs, the manifest, the journal, the protected records (Part 3) and the rendered forms. |
| X3 | **Look, then manifest, then go.** A run first only reads (the look steps of Part 4). From what it read it builds the manifest: the catalog rows that apply, in order, with their targets filled in, including every conditional row that might apply (a row with a "when" clause). The preview is rendered from the manifest and nothing else. The owner's go is recorded with the manifest's hash. Execution refuses a manifest whose hash differs and any operation the manifest does not hold. |
| X4 | **A manifest never changes after the go.** Anything that would add, drop or retarget a row ends the run as `stopped`; a new run looks again, previews again and needs a new go. Conditional rows are how a known fork (a terms page, a tool with no rename) is approved in advance. |
| X5 | **A probe only reads, and has five answers.** For a row whose effect turns state B (the row's "acts on" column) into state A: `before` (the target is in B), `done-ours` (in A, with evidence from Part 2 that this run did it), `done-found` (in A, with no such evidence), `other` (in neither B nor A), `unknown` (the read failed, was partial, was on the wrong account, or timed out). No sixth answer and no inference from time. |
| X6 | **What the executor does with each answer.** `before`: write the intent, apply the effect, run the check, write the result. `done-ours`: nothing; go on. `done-found`: write a `found` line; go on; **the row gets no way back**, and every form that lists what the run did lists it as found, not done. `other`: stop the run and name what is there. `unknown`: stop the run and name the row and what the owner can check. |
| X7 | **The intent holds everything the way back and the next probe need, and it is on disk before the effect.** Every span about to change with its before-image AND its after-image (the after-image is computed before the effect, never read back from the result), the position of a line about to be removed, the whole definition of a thing about to be cancelled, the state the provider reported. A line is appended, flushed and synced with its directory before the step it describes. A result line adds only what was observed (an id, a hash, a state). A cut-off last line is discarded on read and its row is then probed like any other. |
| X8 | **An effect is conditional on its before-state by construction.** A file is created exclusively. A folder is moved by the system's exclusive rename (it fails if the target exists); where the platform has none, the row stops. A provider create is one that fails when the name exists. A shared local file is changed under an advisory lock by writing a new file and swapping it in only if the old file's hash is the one the intent recorded (the remaining race is RK2 in Part 6). An effect that cannot be made conditional is not in this catalog; another effect is used (row SR09 is the example: the hosting project is made by a create call that fails on a taken name, never by a link that adopts). |
| X9 | **An intent with no result is resolved by the probe, and a create is never sent twice on a guess.** For a row that changes an existing thing: `before` means the effect did not land, apply it; A means `done-found` (X6). For a create whose provider refuses a second thing of the same name ("name-unique" in the catalog): the same. For a create that is not name-unique (the database): the row stops as `unknown` until all three hold: the child that sent it is known dead, the provider's request window has passed (a number per provider, Part 6), and a complete authenticated listing shows nothing made for this project. Then, and only in a new run with a new go, the create is offered again. If the listing shows one, the row stops and the owner answers whether it is this project's (an owner-answer row). |
| X10 | **Order comes from each row's "after" column,** never from position alone. A row runs when every row it names is `done-ours` or `done-found`. A row whose dependency is waiting on the owner is written as `blocked` and skipped. |
| X11 | **Two kinds of owner row.** An owner-action row (accept a terms page, rename in a dashboard, pause in a dashboard) is complete when its read-only probe shows state A, and by nothing else: his saying "done" only asks the run to probe again; a probe that shows A without his saying anything completes it. An owner-answer row (confirm a name, give the reason, say whether a found resource is this project's) is complete when his typed answer is recorded. The script never performs either. |
| X12 | **A probe tests only durable facts.** Each row's "durable facts" are the facts no later row of the same manifest changes. The full check (hashes, counts) runs once, right after the effect, and its values go in the result. On a rerun the probe decides `done` from the durable facts alone, so a later row's approved change is never read as drift. |
| X13 | **How a run ends.** `complete`: every row is `done-ours` or `done-found` and every check row passed. `waiting`: nothing runnable is left and at least one owner row is incomplete; each is listed with its exact step; the lock is released; a rerun starts from the probes. `stopped`: a row answered `other` or `unknown`, a check failed, or X4 applied; the summary says which rows finished, and for sunset names both ways on (rerun forward, or restore over the finished rows). |

## Part 2. Evidence that the run did it

An intent line plus a matching state proves nothing about who acted: the run can die after the
intent and before the effect, and the owner can then do the same thing by hand. So:

| Evidence | What it is | Makes a row `done-ours` |
|---|---|---|
| E1 | a durable result line of this run for the row, and the row's durable facts still hold | yes |
| E2 | a marker the effect itself carries: a file naming the run and the row, written inside a folder under the intent and moved with it by the exclusive rename | yes, with the durable facts |
| E3 | an id the provider assigned in the create call's own answer, recorded in the result (a case of E1), and the provider's read of that id showing the expected account | yes |
| E4 | the owner's recorded answer that a found resource, shown to him by its id, is this project's (X9, X11) | yes, for that resource; the answer is the evidence |
| none | an intent with no result and state A | no: `done-found`. For sunset this means restore will not reverse that row and says so |

The cost of the last line is accepted on purpose: a run killed in the instant between an effect
and its result line loses the right to reverse that one effect, and tells the owner. The other
choice is a restore that can reverse something the owner did himself.

## Part 3. Secrets

| Rule | |
|---|---|
| K1 | A secret is a provider token, a database password, a value of an env file, a key or certificate file, and anything inside a record the run copies for the way back (a schedule's command, a launch agent's file, a memory note). |
| K2 | **Channels.** The hosting token is read in-process (the environment variable, else the hosting tool's own credentials file, read only, by one function: ruled, A2), used in a request the frame makes itself to the provider's fixed host over TLS with no redirect followed and no request logging, and dropped. The database password goes to `pg_dump` in a private password file: created exclusively, owner-only, in a private folder of the run, named to the tool by a path in its environment, removed when the tool ends and by the next run's start if a kill left it. The host, port, database and user are not secrets and are ordinary arguments. `gh` keeps its own token; the frame never asks for it. |
| K3 | **Never.** A secret is never an argument of any child, never in any child's environment, never in the journal, the manifest, a form, a trace, standard output, standard error or an error message. Every child starts with a minimal, listed environment that drops the session's debug variables; the runner refuses a known debug or verbose flag and refuses a registered secret, whole or in part, in an argument. |
| K4 | **Nothing a provider's tool prints is kept or shown.** From each command the frame keeps validated fields only: the exit code, ids, states, counts, key names, and an error kind from a fixed list (`not-found`, `auth`, `conflict`, `terms`, `timeout`, `other`). There is no "filtered tail". An error shown to the owner or the executor is the row, the error kind and the command with its non-secret arguments, so he can run it himself in his own terminal and read the tool's words there. An unexpected exception is reported as its type and the row; its message text is never printed. |
| K5 | **The permitted secret stores, and no other file may hold a secret:** the pulled env file in the working tree (ignored by git, proven before every commit; owner-only); the database dump, the saved hosting env values and the memory copy in the sunset folder beside the archived repository (owner-only, outside every working tree; ruled, A2); the protected way-back records in the run directory (owner-only; referenced from the journal by hash, never inlined); the private password file while its tool runs. A permitted store with wider permissions is a failure. Each is created exclusively and never through a symbolic link. |
| K6 | **Inputs are validated before they are stored.** An input that fails the secret check (a pasted address with a password in it) is refused at the start; nothing is stored raw. |
| K7 | **Before every commit the frame scans what will be committed, by content, and before the push every commit to be pushed.** A hit stops the run before the push, naming the file and showing nothing. |
| K8 | **In tests,** the fake HTTP host records that an authorization header arrived and whether its hash equals the expected token's hash; it never stores the header. That is the authorized transmission, and it is the only place a test may see the token leave the frame. Every other place is scanned: every file under the fixture home and the fixture working tree, both output streams, every argument and environment every fake recorded for itself and for anything it started, every git object. A canary found outside a permitted store, or in a permitted store with wider permissions, fails. The scan looks for the canary whole, for each component, and for the percent-encoded and base64 forms of both. |

## Part 4. The catalog

Columns. **Row**: the id. **Class**: `local` (inside the project's own folder), `machine`
(elsewhere on this machine), `remote` (a provider write, shown in the preview with the account the
provider's identity read reports), `owner-action`, `owner-answer`, `check` (reads and decides,
changes nothing). **After**: the rows that must be done first (X10). **Acts on**: state B, the only
state the effect may be applied to. **Effect**: what it does, conditional by construction (X8).
**Durable facts**: what a probe tests for state A (X12). **Evidence**: from Part 2. **Way back**:
the restore row, or `none` with the reason. Sunrise rows have no way back as a command (ruled, A2:
no sunrise undo), so their "way back" column says what the stopped-run summary tells the owner.

### 4.0 Look steps (every run, before the manifest; nothing here changes anything)

| Step | Reads | A failure |
|---|---|---|
| G1 the gate | the vault's four checks of v1 (present, its marker file, its projects folder, not inside a synced documents folder) | ends the run before anything else, the cue included; nothing is created |
| G2 the cue | plays the sound and prints the one-line stamp after G1 passes; never an operation, never blocks | ignored |
| G3 names | the name forms (sunrise) or the project resolved on every layer (sunset, restore); shown and confirmed by an owner-answer | ends the run |
| G4 tools and accounts | each provider's identity read, the git identity, the tools on the path | ends the run with the missing piece named |
| G5 capabilities | what the harness adapter declares it can do: the canary line, listing and cancelling routines, the memory stores | never a failure: an absent capability is carried into the manifest, the preview and the summary as "not available on this harness" |
| G6 probes | the probe of every row that may apply | `other` or `unknown` here ends the run before any preview |
| G7 the owner's words | the one-line description (sunrise) or the reason (sunset): owner-answer | ends the run |
| G8 git safety (sunset) | uncommitted changes and unpushed commits | an owner-answer: he commits and pushes and reruns, or says to archive as it is; never decided by the script |
| G9 the database (sunset) | over the connection the dump will use: the server's own identity, the list of every schema and table that is not the system's, whether the connecting role can read each; and from the provider's side, the resource the idle row would target | decides rows T03 and T22 before the preview: see those rows. Nothing about the database is decided after the go |
| G10 found states (sunset) | each provider resource's state as found; each schedule tied to the project; loose ends (other hosting, other trackers) | a resource found already archived or paused gets no row in the manifest and is listed as "found already retired"; loose ends are listed and never acted on |

### 4.1 Sunrise

Project types (ruled, A1): web app, static site, desktop app, script or CLI. "Hosted types" are
the web app, the static site, and the desktop app (as the holder of the database's keys only).
The database rows apply by the type's default and the `--no-db` flag.

| Row | Class | After | Acts on (B) | Effect | Durable facts (A) | Evidence | If the run stops here, the summary says |
|---|---|---|---|---|---|---|---|
| SR01 make the project folder | local | the go | no path of that name under the developer root (or, with `--promote`, the named folder exists: then this row is `done-found`) | create the folder exclusively | the folder exists | E1 | the folder exists and what is in it |
| SR02 scaffold | local | SR01 | the folder is empty | run the one scaffolder command the preview showed | the scaffolder's own manifest file exists | E1 | a half-run scaffold is `other`: the owner empties the folder or reruns with `--promote` |
| SR03 seed the doc kit | local | SR02 | each of the six kit files either absent, or present as the scaffolder left it | absent: create exclusively. Present: merge by v1's rules (a framework block stays inside its markers; a `CLAUDE.md` with a body is lifted into `AGENTS.md`); a merge is shown to the owner first (an owner-answer row SR03a, "when a kit file exists") | each kit file holds its required lines (the kit check's three script lines) | E1 | which files were written or merged |
| SR04 the ignore rule | local | SR03 | the ignore file lacks the last line that keeps the example env file tracked | swap in the file with that line last (X8) | the git ignore proof passes: the example file not ignored, the local env file and the host's folder ignored | E1 | the proof's result |
| SR05 the repository | local | SR04 | not a repository, or a repository holding only the scaffolder's own commit | initialize on `main`, or rename the scaffolder's branch to `main` | a repository on `main` | E1 | the branch and head |
| SR06 adopt a staged doc (one row per doc) | machine | SR05 | the staged file present, the target path absent | exclusive move into the repo's docs folder under v1's name and date rule | the target present, the source absent | E1 | the doc's new path; moved back by hand if wanted |
| SR06a which doc | owner-answer | SR05 | when two staged docs fit one role, or a doc has no date anywhere | he picks; never the script | his answer recorded | E4 | nothing moved |
| SR07 first commit | local | SR06 | the tree has uncommitted kit, scaffold or adopted files | scan (K7), prove the ignore rule, commit | a commit exists and the tree is clean | E1 | the commit id |
| SR08 the remote repository | remote, name-unique create | SR07 | no repository of that name on the account | create it empty and private (public with `--public`), with no push | the repository exists | E3 | the repository's address and that it is empty |
| SR09 the hosting project | remote, name-unique create | SR08 | no project of that lowercase name on the team; hosted types only | create by the provider's create call, which fails on a taken name; never a link that adopts | the project exists | E3 | the project's id |
| SR10 link the tree | local | SR09 | the working tree has no link file | write the link to the id SR09 recorded | the link file holds that id | E1 | the link file's id |
| SR11 connect the repository to the project | remote | SR10 | the project has no repository connected | connect by id | the provider's read shows our repository's id | E1 | connected or not |
| SR11a allow the host to see the repository | owner-action | SR10 | when SR11's probe shows the host's GitHub app cannot see the repository | the exact GitHub step is shown | the same read as SR11 becomes possible | readback (X11) | the step, still to do |
| SR12 settle the tree | local | SR11 | the tree differs from what the push must carry | re-assert the ignore line as last; placeholder files (desktop app); the lines later layers need in tracked files; scan; commit | the tree clean, the ignore proof passes | E1 | the commit id |
| SR13 the kit check | check | SR12 | | the three script lines; and the canary line through the adapter where G5 declared it | passes when the three lines pass and the canary is `pass` or `not available`; a canary `fail` stops the run | its result line | which line failed |
| SR14 the scan before the push | check | SR13 | | K7 over every commit to be pushed | passes or stops | its result line | the file named, nothing shown |
| SR15 the one push | remote | SR14 | the remote holds no commit, and the local head is the commit SR14 scanned | push `main`, not forced (a remote that gained a commit refuses it) | the remote's head is that commit | E1 | pushed or not; this is the only push (E16-9) |
| SR16 the deployment | check | SR15 | hosted types | wait for the build of that commit; read the clean production address | 200 there, and the deployment's commit is SR15's | its result line | the address and what it answered |
| SR17 the database | remote, NOT name-unique create (X9) | SR11 | no database resource connected to the project | the marketplace's provision, connect and pull, named `<slug>-db` where the tool takes a name | a resource connected to the project | E3 | the resource's id, or `unknown` under X9 |
| SR17a accept the terms | owner-action | SR11 | when the provision answers `terms` | the address to open is shown | the provision's read-only eligibility check passes | readback | the address, still to do; rows that do not need the database go on meanwhile |
| SR17b provision after the terms | remote | SR17a | as SR17 | as SR17; this is the approved retry, a row of its own | as SR17 | E3 | as SR17 |
| SR18 the database's name | owner-action | SR17 | when the tool took no name and the resource is not named `<slug>-db` | the exact clicks are shown | the name reads back as `<slug>-db` | readback | the clicks, still to do |
| SR19 the env file | local, permitted store | SR17 | no local env file at the type's path | the hosting tool's pull writes it; then owner-only | the file exists, ignored, owner-only, and holds the required key names (names only are read) | E1 | present or not |
| SR20 the vault folder and its seed | machine | SR07 | no folder of that slug in the vault's projects folder | create exclusively; write the seed exclusively | the folder and the seed exist | E1 | the folder's path |
| SR21 the vault's root index line | machine, shared file | SR20 | the index has no line for the project | swap in the file with the one line under its heading (X8) | the line is present once | E1 | written or not |
| SR22 the home memory note | machine | SR07 | no note of that name; G5 declares the memory stores | create exclusively | the note exists | E1 | the note's path |
| SR23 the memory index line | machine, shared file | SR22 | the index has no line for the project | swap in with the line (X8) | the line is present once | E1 | written or not |
| SR24 the shortcut line | machine, shared file | SR07 | no alias, function, builtin or program of that name; the shortcut file exists and is wired in | append the one line in v1's exact shape (X8) | the line is present once and a fresh shell knows the alias | E1 | written or not |
| SR25 the end proofs | check | SR16, SR19, SR13 | | the push landed (SR15), the address answered for that commit (SR16), the env file holds its key names (SR19), the kit check passed and its three script lines pass again on the pushed tree | all hold | result lines, one per proof | which proof is missing |

Git commands that change a repository or a remote, in sunrise: SR05 (init or branch rename), SR07
and SR12 (commits), SR08 (create), SR15 (the one push). The manifest lists them; the fakes' record
must equal that list.

### 4.2 Sunset

One order, enforced by the "after" column: preserve (T01 to T05), the barrier, retire on this
machine (T10 to T19), retire at the providers (T20 to T22), the tombstone last (T30). **The
barrier:** no row from T10 on runs until every one of T01 to T05 that the manifest holds is
`done-ours`. Nothing before the barrier moves, removes or pauses anything, so a stop there leaves
the project live. A stop after it leaves the partial state X13 describes. Every row after T12
resolves the repository's path from T12's result, never from the old path. The `--keep-*` flags
drop their rows from the manifest; the preview says so.

| Row | Class | After | Acts on (B) | Effect | Durable facts (A) | Evidence | Way back |
|---|---|---|---|---|---|---|---|
| T01 the dated tag | remote | the go | the remote has no tag of that name; the repository is not archived | tag the head locally and push the tag (a new ref; the remote refuses an existing one) | the remote has the tag at the recorded head | E1 | none: a tag is history |
| T02 the sunset folder | machine | the go | no folder `<Name>.sunset-<date>` beside the archive path | create exclusively, owner-only | the folder exists, owner-only | E1 | none: it holds the copies, which stay |
| T03 the database dump | machine, permitted store | T02 | no dump file in the sunset folder; G9 read a database | `pg_dump` in its archive format, every schema G9 listed, one snapshot, password by K2, written exclusively | the file exists, owner-only | E1; the result holds size, hash, and each table's row count from that snapshot | none: a copy stays. Its checks: the tool exited 0; the tool's own lister reads the archive to its end; every table G9 listed is in it. A miss stops the run at the barrier |
| T04 the hosting env values | machine, permitted store | T02 | no values file in the sunset folder; the project has a hosting project | read every environment's values in-process (K2) and write them exclusively, owner-only | the file exists, owner-only | E1; the result holds the key names per environment and the file's hash, never a value | none: a copy stays |
| T05 the memory copy | machine, permitted store | T02 | no memory folder in the sunset folder; the project has its own memory store (G5) | copy the store into the sunset folder | the folder exists | E1; the result holds each file's hash, equal to the source's | none: a copy stays. V09 restores the working store from it |
| T10 cancel a schedule (one row per schedule) | machine, or through the adapter | the barrier | the schedule is active as G10 found it | a crontab line: swap in the file without it (X8). A launch agent: unload it and move its file into the sunset folder by exclusive move (Q7, Part 6). A harness routine: cancel through the adapter where G5 declared it; otherwise the row is an owner-action with the routine named | the schedule is not active; a moved file carries E2 | E1 or E2; the intent holds the whole definition as a protected record | V14 |
| T11 remove the shortcut lines | machine, shared file | T10 | the shortcut file holds the lines whose target is the repository, as G6 read them | swap in the file without them (X8); the intent holds each line verbatim | no line targets the repository; a fresh shell does not know the alias | E1 | V13 |
| T12 move the repository | local | T11 | the repository at its path with the head G8 passed; no path of that name in the archive folder | write the marker inside it (E2), then exclusive move | the old path absent; the archive path is a repository whose head is the recorded commit | E1 or E2 | V01 |
| T13 move the vault folder | machine | T12 | the folder in the projects folder; no folder of that slug in the vault's archive | write the marker inside it (E2), then exclusive move | the old path absent; the archive path holds the project's index file | E1 or E2 | V02 |
| T14 the index file's status | machine | T13 | the moved index file's status span is the active one | swap in with status archived and the archived date (X8); the intent holds both images | the status span is the archived one | E1 | V03 |
| T16 the vault's root index | machine, shared file | T13 | the project's line under the active heading | swap in with the line under the archived heading (made if missing); both images and the two positions in the intent | the line is under the archived heading | E1 | V05 |
| T17 repoint a link (one row per note that links to the old path) | machine | T13 | the note holds the old path, as G6 read it | swap in with the new path (X8); both images in the intent | the span is the new path | E1 | V06 |
| T18 the home memory note | machine | the barrier | the note's status is active | swap in with status archived and the date | the status span is the archived one | E1 | V07 |
| T19 the memory index line | machine, shared file | T18 | the line under the active list | swap in with the line under the archived heading | the line is under the archived heading | E1 | V08 |
| T20 archive the repository at GitHub | remote | T01, T12 | G10 found it not archived | archive it; the attribution is this invocation's own `before` read, the call's success and the readback (the remaining race is RK3, Part 6) | the provider reports archived | E1 | V10 |
| T21 pause the hosting project | remote | T04, T12 | G10 found it live | the pause request (K2); attribution as T20 | the provider reports paused | E1 | V11 |
| T22 idle the database | owner-action (Supabase: his dashboard step, as v1); `remote` only for a provider whose tool the frame already has | T03 | in the manifest only when G9 bound the dump's database to this resource AND found every schema and table readable; G10 found it live | the exact clicks are shown; the script idles nothing it cannot read back | the provider reports paused, where the frame can read it; otherwise an owner-answer that he did it | readback, or E4 | V12 |
| T30 the tombstone | machine | every earlier row done, found, blocked or waiting | no tombstone in the moved vault folder | render it from the journal (Part 5) and create it exclusively | the file exists | E1 | none: it travels with the vault folder and is kept as history (V04 adds a line to it) |

What G9 decides, so nothing about the database is decided after the go:

| G9 finds | T03 | T22 | The preview says |
|---|---|---|---|
| the database bound to the provider resource, every schema and table readable | in | in | backed up, then paused |
| every schema and table readable, but the database cannot be bound to a resource (a provider with no integration, or names that do not match) | in | **not in the manifest** | backed up; sunset will not pause this database, and the step the owner can take himself |
| a schema or a table the connecting role cannot read | in, as a partial dump | **not in the manifest** | the backup is partial, the unreadable names listed; not paused; the owner's go covers that, or he stops and fixes the role |
| no database, or `--keep-db` | not in | not in | no database row |

A dump that fails its own checks (the tool's exit, the lister, a listed table missing) stops the
run at the barrier whichever line applied. There is no other outcome for an unbound database.

Git commands that change a repository or a remote, in sunset: T01 (a tag and its push), T20 (the
archive). Never a push to a branch.

### 4.3 Restore

Restore reads the sunset run's journal (found in the state folder by project name; the tombstone
names the run). It offers a row only for a sunset row that ended `done-ours`; a `done-found` row
(something already retired, or an effect the run cannot prove) is listed in the preview as "left
as found". Restore is a run like any other: looked, previewed, approved, locked, journaled and
resumable. Its order is its own (paths, then providers, then what depends on both), not sunset
backwards. **Moved things move back; copies stay:** the dump, the saved env values, the memory
copy and the tombstone are never removed by restore.

**The span rule, used by V03, V05, V06, V07, V08.** A span sunset changed is put back only when
the file now holds sunset's after-image for that span exactly and exactly once; then the recorded
before-image replaces it and nothing else in the file moves. If the after-image is missing,
changed or present twice, the row answers `other` and stops, showing the recorded before, the
recorded after and the current text. **A removed line has no after-image to find**, so rows that
put a line back (V05, V08, V13, V14) use their own rule, stated in the row: where it goes and
what must not already be there.

| Row | Class | After | Acts on (B) | Effect | Durable facts (A) | Evidence |
|---|---|---|---|---|---|---|
| V01 move the repository back | local | the go | the archive path is the repository with T12's marker; the original path absent | exclusive move; remove the marker | the original path is the repository; the archive path absent | E1 |
| V02 move the vault folder back | machine | the go | the archive path holds the folder with T13's marker; the original path absent | exclusive move; remove the marker | the original path holds it | E1 |
| V03 the index file's status | machine | V02 | the span rule holds for T14's span | swap in T14's before-image | the status span is the active one | E1 |
| V04 a line on the tombstone | machine | V02 | the tombstone, now in the project's vault folder, lacks a restored line | append "Restored" with the date; the tombstone is kept | the line is present | E1 |
| V05 the vault's root index | machine, shared file | V02 | no line for the project under the active heading; the line T16 wrote is present once under the archived heading | swap in with that line removed and the recorded active line added at the end of the active heading's list | the line is under the active heading | E1 |
| V06 a repointed link (one row per T17 row) | machine | V02 | the span rule holds | swap in the before-image | the span is the old path | E1 |
| V07 the home memory note | machine | the go | the span rule holds for T18's span | swap in the before-image | status active | E1 |
| V08 the memory index line | machine, shared file | V07 | no line for the project in the active list; T19's line present once under archived | swap in with the line moved back to the end of the active list | the line is in the active list | E1 |
| V09 the project's memory store | machine | V01 | T05's copy present with its recorded hashes; the working store's path absent or empty; G5 declares the stores | copy the saved store to the working path; the copy in the sunset folder stays | the working store holds those files | E1 |
| V10 un-archive at GitHub | remote | V01 | the provider reports archived | un-archive; attribution as T20 | not archived | E1 |
| V11 un-pause the hosting project | remote | V01 | the provider reports paused | the un-pause request (K2) | live | E1 |
| V12 resume the database | owner-action | V11 | the provider reports paused, or he says so | the exact clicks are shown | reported live, or his answer | readback, or E4 |
| V13 the shortcut lines | machine, shared file | V01 | no alias, function, builtin or program of each recorded name; no line already targeting the repository | append each recorded line verbatim at the end of the file (X8) | each line present once; a fresh shell knows the alias | E1 |
| V14 a schedule (one row per T10 row) | machine, or through the adapter | V01, V10, V11 | the schedule absent | a launch agent: exclusive move of its file back, then load it. A crontab line: append the recorded line if no identical line exists. A routine: recreate through the adapter where G5 declared it, else an owner-action showing the recorded definition | the schedule is active | E1 |

What restore says when a thing is gone, each as a line of the preview and never as an automatic
step: a database removed after its provider's limit ("recreate from the dump": the commands are
shown as an owner-action; a new database is a new resource and the script never makes one in this
step); a hosting project that is gone (the repository and the saved env values are what he
rebuilds it from); an account that can no longer reach a resource (`unknown`, the row stops); an
archive copy or a protected record that is missing or whose hash differs (the row that needs it
stops; every other row is still offered); both the archive path and the original path present, or
neither (`other`, the row stops and names both).

## Part 5. The forms

The CLI's standard output is JSON and nothing else (the contract's E16-15). A form is rendered to
a file in the run directory and named in the JSON; the adapter shows it. The forms are v1's
(`SUNRISE PREVIEW`, `SUNRISE COMPLETE`, `SUNSET PREVIEW`, `SUNSET COMPLETE`, the tombstone, the two
hand-off prompts, the seeded `AGENTS.md`, the one-line `CLAUDE.md` stub, the vault seed, the
memory note, the alias line) with exactly these changes, and any other change is a stop:

| Change | Where |
|---|---|
| every Notion line leaves (ruled, R3) | all forms |
| a layer the run did not have is omitted | previews, summaries, tombstone, prompts |
| the account each remote row acts as | both previews |
| "Not saved" (storage files, GitHub issues, pull requests and releases), shown before the go | the sunset preview; repeated in the tombstone |
| "Saved copies": the sunset folder's path and what it holds | the sunset summary and the tombstone, in place of v1's backup and memory lines |
| "Backup": the four checks' results, and the sentence that a test load was not done | the tombstone |
| "Provider clocks": one line per provider state entered, with its limit or the word unknown | the tombstone |
| "Found already retired" and "found, not reversible by restore" (the `done-found` rows) | the sunset summary and the tombstone |
| "Not available on this harness" (G5) | previews and summaries |
| "Waiting on you": each incomplete owner row with its exact step | any summary of a run that ended `waiting` |
| "To restore": one line naming the `restore` summons and the run, in place of v1's paragraph | the sunset summary and the tombstone |

## Part 6. Measured later, and the risk that is left

Measured, not assumed:

- **M1 (the live join).** Whether the hosting project connects a repository that has no commit yet
  (SR11 before SR15). If it does not, SR11 moves after SR15 by a manifest built that way from the
  start; if a tracked file would have to change after SR15, the run stops for the owner (a broader
  reading of D6, his gate).
- **M2 (before slice 3's brief).** The marketplace's request window for X9: how long after its
  child dies a provision can still land.
- **M3 (before slice 4's brief).** Each provider's retention limit on an archived, paused or idle
  resource, from the provider's own documents, for the tombstone's clock lines. A limit that cannot
  be established is printed as unknown, never as none.

Risk the design names and cannot remove. **The owner accepted RK1 to RK3 and ruled Q7 on
2026-10-12 (the contract's section 18, A4).** How likely each is was never measured.

- **RK1, the tools' own files.** `gh`, the hosting tool and `pg_dump` are the owner's installed
  tools with his own configuration, and they keep their own logs, caches and credential stores as
  they do when he runs them by hand. The frame gives them no secret in an argument or an
  environment, turns off their debug output and reads nothing they print, but it cannot stop a
  tool from writing into its own folders.
- **RK2, a shared file changed by something else in the same instant.** The swap of X8 checks the
  file's hash and then replaces it. An editor or another tool that writes the same file (the
  shortcut file, an index) between those two steps, without taking the advisory lock, loses its
  write. The window is the time between the hash check and the swap; its length is not measured.
- **RK3, a provider state changed by someone else in the same instant.** T20, T21, V10 and V11 read
  the state, then ask for the change. If the owner makes the same change by hand between the read
  and the request, the run records it as its own, and a later restore reverses it.
- **Q7, a launch agent.** v1 says to "unload" one. An unloaded agent whose file stays in place
  loads again at the next login. T10 moves the file into the sunset folder as well, and V14 moves
  it back. That is a change to what v1 does; the owner ruled it so (A4).

Three more rows change what v1 does, each ruled by the owner (A4): SR09 makes the hosting project by
a create call that fails on a taken name, where v1 links under `--yes`; K4 keeps and shows nothing
a provider's tool prints, where v1's model reads and relays it; T30 writes the tombstone last from
the journal, where v1 writes it in its first phase.

## Where each of the second read's findings lands

| Finding | Closed by |
|---|---|
| F1, F2 | Part 2 (an intent and a matching state are never evidence); X5, X6 (`done-found` has no way back); 4.3's first paragraph |
| F3 | X9 |
| F4 | X8, SR09 |
| F5, F16 | X7 (the after-image is in the intent); the span rule and the line rows of 4.3 |
| F7 | X11 |
| F8, F9, F10, F11 | Part 3 (K2 to K5, K8); RK1 for what cannot be closed |
| F12, F15 | T05, V09 |
| F13 | G9 and its table |
| F18 | Part 5 |
| N1 | X5 (`before` is the approved state B) |
| N2 | T30, V04 |
| N3 | G5, SR13 |
| N4 | G9's table |
| N5 | X12 |
