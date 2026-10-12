# E16 design page 3: undo and restore, and a sunset that leans on no clock

Drafted 2026-10-11 by the control room, beside the E16 lane contract
(`2026-10-11-stations-e16.md`, rulings E16-10 and E16-11; the owner's rulings A1 P11 and P16).
**Status: revision 2, after the outside reviewer's first read (findings F5 and F12 to F16 of that
read are answered here, each named where its rule lands), with the owner's rulings of contract A2
applied where the first revision said PENDING. Not yet read a second time.**

## The problem

The plan asks for two things here: the checks "demonstrate ... restoration", and "Sunset's default
preserves records without depending on a Trash expiration window." The owner's ruling P11: save
and check first, pause second, and name every provider clock that still runs.

v1's way back is one paragraph at the end of the tombstone. It has three gaps:

1. **It is not checkable.** Nothing proves the paragraph matches what the sunset did.
2. **It does not hold the details.** Which other vault notes had their links repointed, which
   launch agent was unloaded and from what file, what the crontab line was.
3. **Some of it has a clock.** The one clock v1 states is Notion's trash, and Notion is out. The
   class stays: a paused database or an idle project can have a provider-side retention limit.

The first draft of this page had a fourth gap of its own: it drew one order, described a second in
prose, and the contract kept a third (F12). There is one order now, below.

## Two words kept apart

- **Undo** is the way back of one operation inside a run that is still going or was interrupted.
- **Restore** is the way back of a finished sunset, days or years later.

Sunrise gets neither as a command (ruled by the owner, contract A2): a half-finished sunrise
resumes forward (page 1), and a project that is no longer wanted is retired by sunset, which never
deletes. A sunrise undo would have to delete a database or a repository made minutes ago, and
"never delete" has no minutes-old exception. Every operation still records its before-state in
its intent (page 1), so a stopped sunrise can say exactly what exists and where.

## What sunset undertakes to preserve

Before the order, the list. For every layer: what the record is, where it lives today, and what
keeps it once the project is retired (F14).

| Record | Lives | Kept by |
|---|---|---|
| the code and its history | the local repository and GitHub | the local repository moved to the archive; the archived GitHub repository; a dated tag |
| work not yet pushed | the local repository only | sunset stops until it is committed and pushed, or the owner says to archive as it is (v1) |
| the database's contents | the provider only | a verified dump in the archive |
| the local env file (development values) | the working tree, ignored by git | it travels with the moved repository |
| the hosting env values for production and preview | the provider only | saved, every environment, to an owner-only file in the archive, never printed (ruled, contract A2) |
| files uploaded to the database provider's storage | the provider only | NOT saved (ruled, contract A2): named in the preview before the go, and in the tombstone |
| GitHub's issues, pull requests and releases | the provider only | NOT saved (ruled, contract A2): they stay on the archived repository; named in the preview and the tombstone |
| the vault notes | the vault | moved to the vault's archive folder |
| the home memory note | the memory store | kept, flagged archived |
| the project's own memory store | a store keyed to the repository's path | copied to the archive |
| the shortcut lines, the schedules | files on this machine, the harness | recorded whole, as protected way-back records, before they are removed |

A record with no entry in the "kept by" column is a stop: sunset does not retire a layer whose
record it has not preserved or named to the owner in the preview he answered. The two NOT saved
rows are the owner's accepted risk: they last as long as the provider keeps
them, and the preview says so every time.

**Where the copies land (ruled, contract A2).** Beside the moved repository, never inside it:

```
 <archive folder>/
 ├── <Name>/                      the repository, moved as it was, nothing added inside
 └── <Name>.sunset-<date>/        owner-only
     ├── the database dump
     ├── the saved hosting env values
     └── the copy of the project's own memory store
```

v1 wrote the dump and the memory copy inside the moved repository, a git working tree where a
broad add would stage them. The tombstone names both folders.

## The drawing: one order, with a barrier

```
 A. LOOK (reads only)
    resolve every layer ─► probe ─► git safety check ─► the reason, in his words
    ─► MANIFEST ─► PREVIEW (names what is not saved) ─► go

 B. PRESERVE (the project stays fully live; nothing is moved, removed or paused)
    record every way-back input in the intents (lines, files, definitions, states)
    push the dated tag ─► verify it on the remote
    dump the database ─► verify it (below)
    save the hosting env values ─► verify key names and hash
    copy the project's own memory store to the archive folder ─► verify hashes

 ═══════════ BARRIER: every check in B has passed, or the run stops here, project live ═══════════

 C. RETIRE ON THIS MACHINE (each step has an exact inverse)
    cancel the schedules      (first: nothing may fire at a path that is about to move)
    remove the shortcut lines
    move the repository to the archive
    move the vault folder, flip its status, write the tombstone, edit the index, repoint links
    flag the home memory note, move its index line

 D. RETIRE AT THE PROVIDERS (each state recorded before and after)
    archive the GitHub repository ─► pause the hosting project ─► idle the database
```

Rules that go with the drawing:

- **A failure in B leaves the project live.** Nothing in B moves, removes or pauses anything. This
  is the only place the page promises "still live" (F12).
- **A failure in C or D leaves a named partial state.** The journal says exactly which operations
  finished. Two ways on from there, both by command: the same sunset resumed forward (page 1), or
  `restore` run over the operations that did finish. The summary of the stopped run names both.
- **B reads from the live paths; C moves them.** Every operation after the repository's move
  resolves paths through the journal's record of the move, never from the old path (F12). The
  dump, the tag and the env save are all in B so that nothing after the move needs the repository
  to be where it was.
- **The memory copy is in B, and v1's rule still holds.** v1 copies the project's memory store
  only after the repository moves, because copying first created the archive path and turned the
  move into a nest. The rule is kept by where the copy lands (ruled, contract A2): beside the
  repository's archive path, in the sunset folder of its own, never inside it, so nothing creates
  the repository's target path before the move and the barrier covers the copy.
- **D follows the order the records need:** the tag is on the remote before the archive (an
  archived repository rejects pushes); the dump is verified before any pause.
- **Already retired by hand.** A provider state found already paused or archived in A is recorded
  as found (page 1: `satisfied`), gets no operation in D and no inverse. A restore will not un-pause
  what the owner paused himself (F2).

## What "verified" means for the backup

v1 checks that the dump file is not empty. The first draft added an exit code, a completion line
and a table count; a dump of the wrong database passes all of those (F13). The checks now:

1. **The same database.** The run reads the database's own identity over the connection it will
   dump (the server's host as connected, the database name, and the provider's reference for the
   resource where the host name carries it). It compares that with the resource the idle step in D
   targets, read from the provider's side. If the two cannot be bound, the dump is still taken and
   kept, **the idle step is taken out of the manifest**, and the preview says sunset will back this
   database up and will not pause it.
2. **The whole of it.** Every schema the connection can read, in the tool's archive format, taken
   in one snapshot. The run lists the archive's contents with the tool's own lister and requires
   every table the live database reports, in that same snapshot, to be there with its row count
   recorded beside it.
3. **Intact.** The tool exited 0; the lister reads the archive to its end; size and hash recorded.
4. **An empty database is said, not assumed.** Zero tables or zero rows is shown in the preview's
   later confirmation as a fact for the owner, and is not a failure.
5. **No test load in this step** (ruled, contract A2). "Verified" is checks 1 to 4. Loading the
   dump into a scratch database would need a database server on the machine; the tombstone says
   in plain words that a test load was not done. The owner carries the risk of a dump that
   passes all four and still fails to load.

Any miss in 1 to 3 stops the run at the barrier (check family L8). The dump is a permitted secret
store (page 2): owner-only, outside any working tree, never printed.

## The clocks

A table the brief for slice 4 fills from the providers' own documents, checked on the day, and the
tombstone prints for the layers a project has. This page does not assert the numbers (contract
Q6). A clock the brief could not establish is printed as "unknown", never as "none", and the
record behind it must then be in the "kept by" column above.

| Provider state sunset enters | Retention limit | Lost when it runs out | Preserved instead |
|---|---|---|---|
| GitHub repository archived | to be measured | to be measured | the local repository in the archive; issues, pull requests and releases are not saved |
| hosting project paused | to be measured | to be measured | the repository; the saved env values |
| database paused or idle (Supabase) | to be measured | to be measured | the verified dump; storage files are not saved |
| database idle (a provider with no integration) | to be measured, per provider | to be measured | the verified dump |

## Restore records, written before the way out is taken

Each sunset operation writes what its inverse needs **in its intent line, before the effect**
(F5; page 1), and adds what it observed in its result:

| Sunset operation | In the intent (before) | In the result (after) |
|---|---|---|
| move the vault folder | both paths; the folder's content hash | the marker written in the target |
| flip the status, write the tombstone | each changed span, before | each changed span, after |
| edit the root index; repoint links in other notes | each file's hash; each span, before | each span, after |
| flag the home memory note; move its index line | each span, before | each span, after |
| copy the project's memory store | the source path, the file list with hashes | the copy's hashes |
| cancel a schedule | the whole definition, as a protected record | the cancelled state as read back |
| move the repository | both paths; the head commit; the remote's address | the marker written in the target |
| remove the shortcut lines | each line verbatim with the file's hash | the file's new hash |
| push the tag; archive the repository | the tag; the repository's id; its state before | its state after |
| pause the hosting project | the project id, the team id; its state before | its state after |
| back up and idle the database | the identity of check 1; the key name the string was read from | the dump's path, size, hash, counts; the state after |

These records are the restore manifest (P16, ruled yes).

## Restore is its own order, not sunset backwards

Running sunset's steps in reverse would bring the shortcut and the schedules back before the
repository they point at (F15). Restore has its own dependency order:

```
 A. LOOK      read the restore manifest ─► probe every layer ─► PREVIEW ─► go
 B. PATHS     move the repository back ─► move the vault folder back ─► undo the recorded spans
              ─► un-flag the memory note
 C. PROVIDERS un-archive the repository ─► un-pause the hosting project ─► resume the database
 D. LAST      put the shortcut lines back ─► recreate the schedules (nothing fires until
              the paths and the providers are back)
```

A restore is a run like any other: locked, journaled, resumable, and an interrupted restore is
resumed by running it again (page 1).

**Moved things move back; copies stay.** The repository and the vault folder were moved, so
restore moves them back. The dump, the saved env values and the memory copy were copies; restore
leaves them and the tombstone where they are and says where.

| It finds | It does |
|---|---|
| everything as sunset left it | runs the order above; ends with the project back and the tombstone kept as history |
| a recorded span whose current text equals what sunset left, exactly, and occurs once | puts back the recorded "before" text for that span only (F16) |
| a recorded span that has changed since, is missing, or occurs twice | stops on that operation, shows the recorded before and after and the current text, changes nothing |
| a target that exists (a new project took the old folder name or the shortcut name) | `foreign`: stops and names it, never moves onto it |
| both the archive path and the original path present, or neither | `unknown`: stops and names both paths |
| an archive copy or a protected record that is missing or whose hash differs | stops on the operation that needs it; every other layer is still offered |
| the account can no longer reach a provider resource | `unknown` for that operation; shown as an `owner` step |
| a provider state that is gone (the paused database was removed after its limit) | says so. Recreating a database from the dump makes a new resource, so it is offered in the preview as an `owner` step with the exact commands, and is never run by the script in this step |
| a hosting project that is gone | the same: named, with the repository and the saved env values as what the owner has to rebuild it from |
| a layer sunset skipped (`--keep-local`) or found already retired | has no record for it and does nothing there; the preview says so |
| a schedule to recreate | a launch agent or crontab line is put back from its protected record; a harness routine is recreated only through the adapter and is named as not recreated on a harness without it |

## Proving it

- **The round trip on fakes (L7).** Sunrise a disposable project, sunset it, **assert the retired
  state on every layer**, then restore it. A pass is every layer back: byte-equal where the bytes
  are the run's own, each fake provider back in its live state with no extra create in its call
  record, and the copies still in the archive.
- **Preserve before retire (L8).** A dump cut off; a dump of another database; a tag push that
  fails; a memory copy whose hashes differ. Each stops at the barrier with every fake still in its
  live state and every local path where it was. A dump that cannot be bound to the resource: the
  idle step is absent from the manifest and from the fakes' call record.
- **A kill in C and in D.** After each operation: the stopped run's summary names what finished;
  the rerun completes; separately, a restore from that partial state brings back exactly the
  finished operations.
- **Restore after drift.** The same line edited since; the line moved; the old folder name taken;
  both paths present; an archive copy missing. Each is the stop the table names.
- **Restore after a clock ran out.** The database fake reports its paused copy gone. A pass is
  the restore saying so and showing the owner step, with no create in the fake's call record.
- **Found already paused.** The hosting fake starts paused. A pass is no pause in sunset's call
  record and no un-pause in restore's.
- **The kill sweep** of page 1 runs over sunset and restore as well as sunrise.

## Questions this page leaves

1. What sunset saves from the providers: RULED (contract A2).
2. A scratch load of the dump: RULED (contract A2), not in this step.
3. Where the copies land: RULED (contract A2), beside the repository.
4. No sunrise undo: RULED (contract A2).
5. The clocks table (contract Q6): filled from the providers' documents before slice 4's brief.
6. Whether the tombstone's v1 form keeps its bytes with the restore records beside it. Reading:
   v1's form kept, minus its Notion lines and with its new locations (a listed substitution,
   E16-13); the records live in the restore manifest, so anything that reads tombstones still does.
