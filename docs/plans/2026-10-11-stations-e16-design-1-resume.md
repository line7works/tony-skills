# E16 design page 1: resuming a half-finished run across outside services

Drafted 2026-10-11 by the control room, beside the E16 lane contract
(`2026-10-11-stations-e16.md`, rulings E16-3 to E16-6 and E16-9). A design page is a drawing, not
a brief: it says how the hard part is meant to work and what is still open, so the outside
reviewer can try to break it on paper before a builder writes code. **Status: revision 2, after
the outside reviewer's first read (findings F1 to F7 of that read are answered here, each named
where its rule lands). Not yet read a second time.**

## The problem

A sunrise changes about a dozen places: a folder, a git repository, a GitHub repository, a hosting
project, a database, a pulled env file, a vault folder, an index line, a memory note, a shortcut
line. A sunset changes about as many. Any step can die: the session ends, the network drops, a
provider answers late, the owner has not clicked a terms page yet. v1 says "detect what already
exists and continue". That sentence carries three hard cases it does not name:

1. **Done, but not written down.** The repository was created and the run died before it recorded
   that. A rerun that trusts its notes creates it again, or stops on its own work as a collision.
2. **Written down, but not done.** The notes say the alias line was appended and the file was
   rolled back by something else. A rerun that trusts its notes skips it.
3. **Somebody else's.** A project of the same name already exists on the host. A link under
   `--yes` adopts it without asking. The rerun must tell its own half-finished work from a
   stranger's, and from the owner's own hand-made thing, on every layer.

## Five answers, not four

The first draft let a probe answer `ours` when the world matched what the run would write. That
proves the content, not who made it (F1): the owner can have written the same line himself, and a
way back that treats it as the run's would later remove his line. So a probe has five answers,
and two of them used to be one:

| Answer | Means | What the run may do |
|---|---|---|
| `absent` | a complete, authenticated read on the right account shows the target is not there | apply the effect |
| `satisfied` | the world already matches the wanted state, and nothing shows this run made it so | record it as found, apply nothing, and record **no way back** for it |
| `ours` | the world matches, and there is evidence this run made it so (below) | record the result, keep the way back |
| `foreign` | something is there that does not match, or matches and is known not to be the run's | stop and name it; never overwrite, adopt or move onto it |
| `unknown` | the read failed, was partial, was on the wrong account, timed out, or cannot decide | stop and name the operation and what the owner can check |

Content equality alone can make a thing `satisfied`. It can never make it `ours`.

## The drawing

```
 inputs ──► gate ──► run lock ──► probes ──► MANIFEST ──► PREVIEW ──► go (bound to the manifest's hash)
                                                │
                                                ▼
      for each operation whose dependencies are done, in the manifest's order:
      ┌────────────────────────────────────────────────────────────────────────────────────┐
      │ probe ─► absent ─► INTENT (with the before-state), made durable                      │
      │        │            ─► re-check the precondition ─► effect (no-clobber) ─► check     │
      │        │            ─► RESULT, made durable                                          │
      │        ├─► satisfied ─► FOUND (no way back recorded)                                 │
      │        ├─► ours      ─► RESULT (found done)                                          │
      │        ├─► foreign   ─► STOP, name what is there                                     │
      │        └─► unknown   ─► STOP, name the operation                                     │
      └────────────────────────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
                          summary, rendered from the journal
```

A rerun enters the same loop at the top with the same manifest. Nothing in the loop asks "where
did I stop". Every operation is probed again.

## What counts as evidence that a thing is ours

Evidence comes from two places only: a durable journal line this run wrote, and an identity the
provider itself assigns and never reuses.

| Target | `ours` needs | Without it |
|---|---|---|
| a file the run writes whole | an intent line that recorded "no file here" (or the prior bytes' hash), and bytes now equal to the manifest's | equal bytes with no such intent: `satisfied`. A symbolic link at the path: `foreign` |
| a line the run adds to a shared file | an intent line that recorded the file's hash without the line, and the exact line now present once | the line present with no such intent: `satisfied`. Present twice: `foreign` |
| a moved file or folder | an intent line holding the source's content hash; now the source gone, the target present with that hash, and a result line or the move's own marker file written inside the target by the effect | source gone and target present with no marker and no result: `unknown` |
| a git repository | a result line holding the first commit's id, that commit still the root of `main`, and the working tree's path unchanged | a folder that already was a repository: `--promote`'s case, asked for by name. A repository that appeared with no result line: `unknown` |
| a GitHub repository | a result line holding the id GitHub assigned, read back on the probed account | an intent with no result and a repository of that name now present: `unknown`, always (F2). The run shows its id and asks the owner; his answer is recorded as an `owner-confirmed` line holding that id, and only then is it `ours` |
| a hosting project | a result line holding the project's id, and the provider's own read of that id showing the expected account, team and repository connection | the same: an intent with no result is `unknown` and goes to the owner with the id shown |
| a database resource | a result line holding the resource id, and the provider's read showing it connected to our project | provisioning that may have succeeded with no result line: `unknown`; never a second provision (F3) |
| a paused, archived or idle state | an intent line that recorded the state **before** (live), and the provider now reporting the new state | a resource found already paused or archived before the run touched it: `satisfied`, recorded as found, and no way back: a restore never un-pauses what the owner paused himself |

**No inference from time.** The first draft let a rerun claim an empty repository or project
"created after the intent line's time". An owner can make one by hand in that window, and the two
clocks need not agree (F2). That rule is gone. An intent with no result on a remote create is
`unknown` and costs the owner one answer.

**Absence has to be proven.** After an intent with no result, elapsed time or a lookup that
returns nothing never makes the target `absent` (F3). A provider can report "not found" for a
while after a create. `absent` after such an intent needs what `absent` always needs (a complete,
authenticated read on the right account) and, for a create the provider cannot make idempotent,
the owner's answer as well. A timeout is `unknown`.

## The journal, and what makes it safe to trust

- **One writer.** A run takes an exclusive lock on its run directory and an exclusive lock on the
  project's name before the first probe. A second run of the same project stops at once and names
  the first (F4).
- **Durable before the effect.** A line is appended, flushed and synced to disk, with its
  directory, before the step it describes goes on. A final line that is cut off is discarded on
  read, and its operation is treated as an intent that may or may not have been written: probed,
  and `unknown` unless the probe proves `absent`.
- **The intent carries the way back** (F5). Before any effect, the intent line holds everything
  the inverse will need and everything that cannot be read again afterwards: the exact lines about
  to be removed, the file's bytes or their hash, the schedule's whole definition, the state the
  provider reported. A kill between the effect and the result then loses nothing. Result lines add
  what was observed (an id, a hash, a state), never anything that cannot be recovered.
- **The effect cannot clobber** (F4). A file is created exclusively; a move refuses an existing
  target; a line is added by writing a new file and swapping it in only if the old one's hash is
  still the one the intent recorded. An effect that cannot be made conditional re-checks its
  precondition immediately before it runs, and its check runs immediately after.
- **No secrets, and protected content by reference.** A line holds ids, paths, hashes, states and
  short non-secret text. Content that could hold a secret (a schedule's command, a launch agent's
  file, a copied note) is stored as a protected file and referenced by hash (design page 2).

One line per event: the run id, the operation id, the event (`intent`, `result`, `found`,
`stopped`, `owner-wait`, `owner-confirmed`, `blocked`), the time, and the facts above. The
journal's first line is the manifest's hash, and the go is a line.

The run directory holds the sanitized inputs, the manifest, the journal, the protected files and
the kept fields of each command's outcome (design page 2 says what is kept). It cannot live in
the project: sunrise starts before the repository exists and sunset moves it. It is a per-user
state folder outside every repository, readable by the owner only, one folder per run, resolved in
the one machine-facts module (contract Q1: the owner's call on the place and on how long finished
runs are kept).

## Operations that wait for the owner

Three v1 steps cannot be done by a script: accepting a marketplace's terms the first time, renaming
a database in a dashboard when the tool has no rename, and allowing the host's GitHub app to see a
new repository. A fourth comes from this page: confirming that a half-created remote thing is the
run's. Each is an `owner` operation with these rules (F7):

- **A probe only reads.** Checking whether the owner has done his step never changes anything. The
  first draft's "the terms retry succeeds" was an effect dressed as a probe. The retry of a
  provisioning command is its own `remote` operation in the manifest, with its own intent and
  result, and it runs only after the owner operation it depends on is done.
- **Two things end a wait, in order.** The owner's word that he did it, recorded as
  `owner-confirmed` (E16-4), then a read-only check that the world agrees (the name reads back as
  `<slug>-db`, the connection shows). His word without the readback leaves the operation waiting;
  the readback without his word is recorded as `found` and the wait ends.
- **Dependents are blocked, by name.** The manifest holds each operation's dependencies. An
  operation whose dependency is waiting is recorded as `blocked` and skipped; everything else runs.
  When nothing runnable is left and something still waits, the run ends as `waiting`, never as
  complete. It lists each waiting step with the exact action, and the lock is released.
- **A rerun starts from the readbacks.** A finished owner step is found by its readback and is
  never asked for twice. An action link that has expired is renewed by the retry operation, which
  produces a new `owner-wait`.

## The order, and the one push

E16-9 allows one push to `main` of the new repository. v1 pushes twice: once when the remote is
created, and again at closeout for the edits later layers made. The order below puts every tracked
edit, and the kit check that can force one, before the push (F6):

```
 local:  scaffold ─► seed kit ─► adopt docs ─► init ─► commit
 remote: create the repository EMPTY (no push)
 host:   link the working tree to a new project
 local:  re-assert the ignore-file line ─► placeholder files (desktop app only)
         ─► every line a later layer would write into a tracked file (the host's address form,
            the env instruction) ─► KIT CHECK, all four lines ─► fix and re-check until clean
         ─► secret scan of every commit to be pushed (page 2) ─► commit
 remote: PUSH main once ─► verify the remote's head is the local head
 host:   the build of that commit ─► the clean production address answers 200,
         and the deployment's commit is that head
 host:   database: provision, connect, pull the env file (nothing tracked changes) ─► key names
 local:  vault entry, memory note, shortcut (nothing tracked changes) ─► summary
```

After the push, no operation writes a tracked file. If a real service forces one (the link will
not connect an empty repository and the connection writes a file; a kit line that can only be
checked after the deploy fails), the run stops and shows the owner the edit and the second push it
would need: that is a broader reading of D6 and his gate (contract Q2). The live join measures
whether the link connects an empty repository; if it does not, the connection moves after the push
and the rule above still holds or stops.

End verified means all four of v1's proofs, each as a check with its own result line: the push
landed (the remote's head), the clean address answers 200 for that commit, the env file holds its
key names, the kit check passed before the push and its three script lines pass again on the
pushed tree.

## Proving it

- **The kill sweep.** For every operation of every fake: kill after the intent line, inside the
  effect (the fake dies mid-call), after the effect and before the result line, and after the
  result line. Then rerun. A pass is every operation applied exactly once, the fakes' call records
  showing no second create, every way-back input present in the journal, and a journal that reads
  straight. The sweep runs its points side by side from the first slice.
- **Late and lost answers.** A fake whose create succeeds and whose response is lost, and which
  then reports "not found" for longer than any wait. A pass is `unknown`, the owner asked with the
  id shown, and one resource in the fake's state, never two.
- **The owner's own thing.** Each layer pre-seeded with exactly what the run would write, made by
  the test and not by the run. A pass is `satisfied`, nothing written, and no way back recorded: a
  later restore leaves it alone.
- **Foreign state.** Each layer pre-seeded with a same-named thing that differs. A pass is a stop
  that names it and no write anywhere.
- **Drift and races.** A file the run wrote is edited between the kill and the rerun; a target
  appears between the probe and the effect; two runs start at once. Passes: a stop on that
  operation; the effect refuses; the second run stops on the lock.
- **A torn journal.** The last line cut at every byte. A pass is the same end state as the kill
  sweep's.
- **Waits.** An owner step left overnight, a link that expired, a confirmation with no readback.
  Passes: `waiting` with the dependents named; a new link; still waiting.

## Questions this page leaves

1. Where the run directory lives and how long finished runs are kept (contract Q1). The owner's.
2. Whether the host links an empty repository (contract Q2). Measured in the live join; the stop
   is drawn above.
3. Whether the canary line of the kit check (a model quotes the first line of its instructions)
   can run before the push on both harnesses. Reading: yes, it reads local files; on a harness
   without it the preview and the summary say it did not run (E16-14).
4. Whether a `--promote`d folder that is already a repository with history can ever take E16-9's
   push. Reading: no. A promoted repository with history gets a remote and an ordinary branch and
   pull request, and the preview says so.
