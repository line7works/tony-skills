# E16 design page 1: resuming a half-finished run across outside services

Drafted 2026-10-11 by the control room, beside the E16 lane contract
(`2026-10-11-stations-e16.md`, rulings E16-3 to E16-6 and E16-9). A design page is a drawing, not
a brief: it says how the hard part is meant to work and what is still open, so the outside
reviewer can try to break it on paper before a builder writes code. **Status: DRAFT, not read by
the reviewer yet.**

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
   stranger's, on every layer.

## The drawing

```
 inputs ──► gate ──► probes ──► MANIFEST ──► PREVIEW ──► go (bound to the manifest's hash)
                                   │
                                   ▼
            for each operation, in order:
            ┌──────────────────────────────────────────────────────────────────────┐
            │ probe ──► absent ──► write INTENT ──► effect ──► check ──► write RESULT │
            │       ├─► ours    ──► write RESULT (found done) ──► next                │
            │       ├─► foreign ──► STOP, name what is there                          │
            │       └─► unknown ──► STOP, name the operation                          │
            └──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                     summary, rendered from the journal
```

A rerun enters the same loop at the top with the same manifest. Nothing in the loop asks "where
did I stop". Every operation is probed again, so the three hard cases fall out of the loop:
case 1 probes `ours` and is recorded as found done; case 2 probes `absent` and is done again;
case 3 probes `foreign` and stops.

## What makes a thing "ours"

The probe must tell `ours` from `foreign` without trusting the journal alone. For each kind of
target the operation writes a mark it can read back, or compares content it wrote:

| Target | `ours` means | Why not the name alone |
|---|---|---|
| a file the run writes whole (the seed files, the vault seed, the memory note) | the bytes equal what this manifest would write | a same-named file with other bytes is the owner's or another tool's |
| a line the run adds (the index line, the alias line, the ignore-file line) | that exact line is present once | the file is shared; only the line is ours |
| a moved file or folder (a staged doc, a vault folder, the repo) | the source is gone, the target exists and its content hash equals the hash recorded in the intent | a target that existed before is the nest bug of 2026-09-05 |
| a git repository | the folder is a repository whose first commit this run made (the commit id is in a result line), or one the scaffolder made inside this run's window | a folder that already was a repository is `--promote`'s case, asked for by name |
| a GitHub repository | it exists under the probed account and its id equals the id a result line holds; with an intent and no result: it exists, holds no commit, and was created after the intent line's time | names are reusable; an empty repository created inside the window is the only safe inference |
| a hosting project | the id in the working tree's link file equals the id a result line holds; with an intent and no result: the project exists, has no deployment, and was created after the intent line's time | a link under `--yes` adopts any project of that name |
| a database resource | the resource id a result line holds is connected to our project | the marketplace names resources itself |
| a paused, archived or idle state (sunset) | the provider reports the state and a result line says this run asked for it | a project the owner paused by hand is his state, to be left as found and said so |

An intent line with no result line and a probe that cannot decide is `unknown`, and the run stops
with the operation named and the two things the owner can check. It never guesses.

## The journal

One line per event, appended and flushed before the next step. A line holds: the run id, the
operation id, the event (`intent`, `result`, `found`, `stopped`, `owner-wait`, `owner-confirmed`),
the time, and for a result the facts the way back and the next probe need (an id, a path, a hash,
the exact line). No line holds a secret (design page 2). The journal's first line is the
manifest's hash, and the go is a line.

The run directory holds the inputs as given, the manifest, the journal, and the captured, filtered
output of each command. It cannot live in the project: sunrise starts before the repository exists
and sunset moves it. Proposed: a per-user state folder outside every repository, one folder per
run, named by project and start time, resolved in the one machine-facts module (contract Q1).
A project's finished runs stay there; the summary and the tombstone carry what a person needs.

## Operations that wait for the owner

Three v1 steps cannot be done by a script: accepting a marketplace's terms the first time, renaming
a database in a dashboard when the tool has no rename, and allowing the host's GitHub app to see a
new repository. Each is an `owner` operation: the loop writes `owner-wait` with the exact step,
goes on with every operation that does not depend on it (the manifest holds the dependencies), and
returns to it. The probe is what ends the wait, not the owner's say-so alone: the terms retry
succeeds, the name reads back as `<slug>-db`, the connection shows. A run that ends with an owner
operation still waiting ends as `waiting`, never as complete, and a rerun picks it up.

## The order, and the one push

E16-9 allows one push to `main` of the new repository. v1 pushes twice: once when the remote is
created, and again at closeout for the edits later layers made (the ignore-file lines the link
appends, the placeholder files for an app with no site). Proposed order, so one push carries
everything:

```
 local:  scaffold ─► seed kit ─► adopt docs ─► init ─► first commit
 remote: create the repository EMPTY (no push)
 host:   link the working tree to a new project ─► re-assert the ignore-file line ─► commit
 remote: PUSH main once  ─► the host builds from that push
 host:   database: provision, connect, pull the env file (nothing tracked changes)
 check:  the clean production address answers 200 ─► kit check ─► summary
```

The open point (contract Q2): whether the host's link connects a repository that has no commit
yet. If it does not, the connection step moves after the push and nothing else changes. If a later
layer still must edit a tracked file after the push, that is a second first-day push and a
broader reading of D6: the owner's gate, not the builder's choice. The live join measures it.

## Proving it

- **The kill sweep.** For every operation of every fake: kill after the intent line, inside the
  effect (the fake dies mid-call), after the effect and before the result line, and after the
  result line. Then rerun. A pass is every operation applied exactly once, the fakes' call records
  showing no second create, and a journal that reads straight. The sweep runs its points side by
  side from the first slice.
- **Late answers.** A fake that reports "not found" for a few seconds after a create, as real
  providers do. The probe waits a bounded time before it calls a fresh create `absent`.
- **Foreign state.** Each layer pre-seeded with a same-named thing the run did not make. A pass is
  a stop that names it and no write anywhere.
- **Drift under the run.** A file the run wrote is edited between the kill and the rerun. A pass is
  a stop on that operation (`foreign`: the bytes are no longer ours), never an overwrite.

## Questions this page leaves

1. Where the run directory lives (contract Q1). The owner's, with a recommendation.
2. Whether the host links an empty repository (contract Q2). Measured in the live join; the
   fallback is drawn above.
3. How long a probe waits on a late answer before it stops as `unknown`. A number for the brief,
   set from the providers' documents and from the live join.
4. Whether a `--promote`d folder that is already a repository with history can ever take E16-9's
   push. Reading: no. A promoted repository with history gets a remote and an ordinary branch and
   pull request, and the preview says so.
