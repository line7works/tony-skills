# E16 design page 3: undo and restore, and a sunset that leans on no clock

Drafted 2026-10-11 by the control room, beside the E16 lane contract
(`2026-10-11-stations-e16.md`, rulings E16-10 and E16-11, picks P11 and P16). **Status: DRAFT,
not read by the reviewer yet.**

## The problem

The plan asks for two things here: the checks "demonstrate ... restoration", and "Sunset's default
preserves records without depending on a Trash expiration window."

v1's way back is one paragraph at the end of the tombstone: move this back, flip that, unarchive,
unpause, "restore/unsuspend the database", recreate the schedules. It works when a careful person
follows it soon. It has three gaps:

1. **It is not checkable.** Nothing proves the paragraph matches what the sunset did. A sunset run
   with `--keep-local` or with a layer missing leaves a different way back than the paragraph says.
2. **It does not hold the details.** Which other vault notes had their links repointed, which
   launch agent was unloaded and from what file, what the crontab line was. v1 records the alias
   line verbatim and the cancelled schedules; the rest is left to memory.
3. **Some of it has a clock.** The audit behind the plan found the one v1 states: the Notion board
   goes to a trash that empties in about 30 days. Notion is out of this step by the owner's ruling,
   and every line of v1 that names a trash names Notion's, so that clock leaves with it. The class
   stays: a paused database or an idle project can have a provider-side retention limit, after
   which "unpause" is no longer on offer.

## Two words kept apart

- **Undo** is the way back of one operation inside a run that is still going or was interrupted.
- **Restore** is the way back of a finished sunset, days or years later.

Sunrise gets neither as a command (contract Q5): a half-finished sunrise resumes forward (page 1),
and a finished project that is no longer wanted is retired by sunset, which never deletes. Building
a sunrise undo would mean deleting a database or a repository that was created minutes ago, and
"never delete" has no minutes-old exception. The one place a sunrise operation's way back is used
is a stop: the summary of a stopped run lists what exists and where, from the journal.

## The drawing: sunset preserves first, then idles

```
   PRESERVE (no clock)                              IDLE (may have a clock)
 ┌──────────────────────────────────────┐        ┌─────────────────────────────────┐
 │ unpushed work surfaced, tag pushed    │        │ GitHub: archive (read-only)      │
 │ vault folder ─► archive folder        │        │ host: pause                      │
 │ memory note flagged, store copied     │  ───►  │ database: idle or pause          │
 │ repo ─► archive folder                │  only  │ schedules: cancel                │
 │ shortcut lines recorded               │  after │ shortcut lines removed           │
 │ database dump written AND verified    │  every └─────────────────────────────────┘
 │ restore records written (below)       │  check
 └──────────────────────────────────────┘  passes
```

The rule (E16-10): nothing in the right box runs until everything in the left box that it could
strand has been checked where it landed. A database is idled only after its dump is verified; a
repository is archived only after the tag is on the remote; a schedule is cancelled only after
what recreates it is on disk. A failed check in the left box stops the run with the project still
live, which is the safe side to stop on.

## What "verified" means for the backup

v1 checks that the dump file is not empty. A dump cut off halfway is not empty. Proposed checks,
all by script: `pg_dump` exited 0; the plain-format file ends with the tool's own completion line;
the file's size and hash are recorded; and the tables the dump names are counted against a table
count read from the live database in the same run. Any miss stops the run before the idle step
(check family L8). The dump is the record that has no clock. The provider's paused copy is a
convenience on top of it.

Where it lands (contract Q4): v1 writes the dump and the copied memory store inside the moved
repository's folder. That folder is a git working tree, so a later broad `git add` would stage a
database dump. Proposed: both land beside the repository in the archive folder, in a folder named
for the project and the date, owner-only, with the tombstone saying where. This moves a v1
artifact, so it is the owner's call.

## The clocks

A table the brief for slice 4 fills from the providers' own documents, checked on the day, and the
tombstone prints for the layers a project has. This page does not assert the numbers (contract Q6).

| Provider state sunset enters | Is there a retention limit | What is lost when it runs out | What sunset preserved instead |
|---|---|---|---|
| GitHub repository archived | to be measured | to be measured | the full local repository in the archive folder |
| hosting project paused | to be measured | to be measured | the repository; the env key names (never the values) |
| database paused or idle (Supabase) | to be measured | to be measured | the verified dump |
| database idle (a provider with no integration, P7) | to be measured, per provider | to be measured | the verified dump |

## Restore records, written when the way out is taken

Each sunset operation writes, in its result line, exactly what its inverse needs (E16-11):

| Sunset operation | Recorded for the way back |
|---|---|
| move the vault folder | both paths; the folder's content hash |
| flip the status, write the tombstone | the lines changed, before and after |
| edit the root index; repoint links in other notes | each file, each line, before and after |
| flag the home memory note; move its index line | the lines changed, before and after |
| copy the project's memory store | the source path, the file count, the hashes |
| cancel a schedule | the whole crontab line, the launch agent's file, the routine's definition as the adapter read it |
| move the repository | both paths; the head commit; the remote's address |
| remove the shortcut lines | each line verbatim, and its line number |
| push the tag; archive the repository | the tag, the repository's id |
| pause the hosting project | the project id and the team id |
| back up and idle the database | the dump's path, size and hash; the provider; the resource id; the key name the connection string was read from, never the string |

If P16 is ruled yes, these records are the restore manifest: the inverse operations in reverse
order, each with its own probe, effect and check. `restore <project>` reads it, probes every layer,
renders a preview, takes a go and runs it under the same rules as any run (pages 1 and 2). If P16
is ruled no, the same records render the restoration instructions as a checked list, and the join
demonstrates them by hand.

## What a restore meets, and what it does

| It finds | It does |
|---|---|
| everything as sunset left it | runs the inverse operations; ends with the project back and the tombstone kept as history |
| a line or a file someone edited since (the root index gained other entries) | applies the recorded line-level change if the surrounding lines still match; otherwise stops on that operation and shows both versions |
| a target that exists (a new project took the old folder name or the shortcut) | `foreign`: stops and names it, never moves onto it |
| a provider state that is gone (the paused database was removed after its limit) | says so, and offers what the preserved copy allows: a new database from the verified dump is a new resource, so it is a `remote` operation in the preview, never automatic |
| a layer sunset skipped (`--keep-local`) | has no record for it and does nothing there; the preview says so |
| a schedule to recreate | shows the recorded definition as an `owner` or adapter operation; a routine is recreated only through the adapter, and is named as not recreated on a harness without it |

A restore never deletes the archive copies or the dump. It leaves them, and the tombstone, in
place and says where they are.

## Proving it

- **The round trip on fakes (L7).** Sunrise a disposable project, sunset it, restore it. A pass is
  every layer back: byte-equal where the bytes are the run's own (the alias line at its line, the
  vault folder's hash, the memory note, the index lines), and each fake provider back in its live
  state with no extra create in its call record.
- **Restore after drift.** Edit the root index and the shortcut file between sunset and restore;
  take the old folder name. Each is a plain stop or a clean merge as the table says.
- **Restore after a clock ran out.** The database fake is told its paused copy is gone. A pass is
  the restore saying so and offering the dump as a new-resource operation that waits for a go.
- **Preserve before idle (L8).** A dump that is cut off, a tag push that fails, a copy whose hashes
  differ. Each stops the run with the right box untouched, shown by the fakes' call records.
- **The kill sweep** of page 1 runs over sunset and restore as well as sunrise.

## Questions this page leaves

1. Where the dump and the copied memory store land (contract Q4). The owner's.
2. No sunrise undo (contract Q5). The owner's, with a recommendation.
3. The clocks table (contract Q6): filled from the providers' documents before slice 4's brief.
4. Whether a restore that must create a new database from the dump is in this step at all, or is
   named in the preview as a step the owner takes by hand. Reading: named and offered, built only
   as far as the fakes prove it; the live join does not exercise it.
5. Whether the tombstone's v1 form keeps its bytes with the restore records added below it, or
   moves to a new form. Reading: v1's form kept (minus its Notion lines), the records in the
   restore manifest beside it, so anything that reads tombstones today still does.
