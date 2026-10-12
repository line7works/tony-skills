# E16 design page 2: keeping credentials out of logs, traces and error output

Drafted 2026-10-11 by the control room, beside the E16 lane contract
(`2026-10-11-stations-e16.md`, ruling E16-7; plan amendment A8: "the script extraction tests the
tracing and error-output paths for credential exposure"). **Status: revision 2, after the outside
reviewer's first read (findings F8 to F11 of that read are answered here, each named where its
rule lands), with the owner's rulings of contract A2 applied. Not yet read a second time.**

## The problem

Moving v1's commands into scripts makes a new risk. In v1 a model types a command and the secret
passes through one shell line. In v2 a script runs the command, writes a journal, keeps the
command's outcome for a resume, renders a preview and a tombstone from what it kept, and reports
errors. Every one of those is a place a token or a connection string can come to rest, and some of
them are files that outlive the run or get pasted into a chat. The repository is public and the
run directory is read by a model.

## The secrets a lifecycle run meets

| Secret | Where it comes from | Who needs it |
|---|---|---|
| the hosting token | an environment variable, or the hosting tool's own credentials file | the pause and unpause requests |
| the GitHub token | held by `gh` in its own store | `gh` only; the core never asks for it and never sees it |
| the database connection string, and the password inside it | a key in the project's env files, or the hosting tool's env pull | `pg_dump` |
| the pulled env file's values | written by the hosting tool into the working tree | the project, later; the run needs only the key names |
| a key or certificate file, or a secret in any file, in the working tree | the owner or a scaffolder | nobody in the run; it must never be committed |
| a secret inside something the run copies or records for the way back | a schedule's command line, a launch agent's file, a memory note | nobody; it must be kept without being exposed |

The run knows the exact value of some of these (the token, the connection string). It never knows
others (the GitHub token, the env file's values, a secret in a copied note). The first draft's
guard was built on knowing the value. This revision does not depend on it.

## Three rules, in order of strength

1. **Do not put it there.** A value that never enters a place cannot leak from it. This is the
   rule the others back up.
2. **Keep fields, not text** (F9). What a provider's tool prints is treated as secret-bearing by
   default and is not kept. From each command the run keeps only fields it has validated: the exit
   code, ids, states, counts, key names, and an error **kind** from a fixed list (`not-found`,
   `auth`, `conflict`, `terms`, `timeout`, `other`). The summary and the stops are written from
   those fields.
3. **Filter what little text is kept.** Where diagnostic text must be kept for a person (the tail
   of a failed command, shown on the owner's request), it passes one filter over the whole captured
   output at once, never chunk by chunk. The filter removes every registered value, each
   **component** of it (the password alone, the user and password pair), each in its plain,
   percent-encoded and base64 forms, and then key shapes as a last net. Text that came through the
   filter is marked as filtered wherever it is shown.

## Where a secret can leak, and the rule for each

| Sink | How it leaks | Rule |
|---|---|---|
| a command's arguments | v1 runs `pg_dump "<connection string>"` and `curl -H "Authorization: Bearer <token>"`; arguments are readable by other processes and are printed by a failed-command error | a secret is never an argument. The runner refuses to start a child whose arguments hold a registered value or one of its forms |
| a child's environment | an environment is also readable by other processes of the same user, and is inherited by whatever the child starts (F8) | every child gets a minimal, listed environment, never the run's own. No secret is placed in it. `pg_dump` reads its password from a private password file (below); the hosting request has no child |
| the journal and the manifest | recording "what I ran" or "what the provider said" | rule 2: fields only. Operations name secrets by a label (`host-token`, `db-password`) |
| kept command output | a provider echoes a connection string in an error, whole, in part or encoded | rule 2: not kept. Rule 3 for the tail shown on request |
| error text and tracebacks | an exception message carries a URL with a password in it, or the failed command line | errors are built from the operation's label and an error kind, never from the raw exception; an unexpected exception is reported as its type and the operation, and its text goes through rule 3 |
| the trace | a lifecycle trace would record each command | the trace records the operation id, the tool's name and the error kind; never arguments, never an environment |
| the saved inputs | the run directory keeps the inputs "as given", and an input can hold a secret (a pasted address with a password) | inputs are validated to a schema before they are stored; a field that fails the secret check is refused at the start with a plain message, and nothing is stored raw (F10) |
| records for the way back | a cancelled schedule's command, a launch agent's file, a copied memory note can hold a token (F10) | they are never inlined in the journal. Each is stored as a protected file (owner-only, in the run directory or the archive) and referenced by hash; a preview or a tombstone shows the name and the hash, never the content |
| the preview, the summary, the tombstone, the restore manifest, the hand-off prompt | rendered from the journal | safe if the journal is; scanned anyway |
| the standard output the model reads | a script that "confirms the env file is non-empty" by printing it | a check on a secret-bearing file reads key names and counts only |
| a shell or tool trace flag | `set -x`, a tool's verbose or debug flag, a debug variable inherited from the session | forbidden; the minimal environment drops inherited debug variables and the runner refuses a known debug flag |
| a tool's own side files | a provider's tool writes a debug log, a cache or a crash report somewhere of its own (F10) | each provider module lists the side files its tool is known to write; the tools run with their own config and cache locations left alone (they are the owner's), and the module's tests run the fake with a fixture home and scan all of it (below) |
| the hosting request itself | an HTTP client follows a redirect and sends the token to another host, or logs the request (F10) | the request goes only to the provider's fixed host over TLS, follows no redirect, and its client logs nothing |
| a symbolic link under an output | the backup or the env file is written through a link someone placed, to a place the run did not mean (F10) | secret-bearing files are created exclusively, owner-only, never through a link; an existing path stops the operation |
| git | a scaffolder commits a secret before any guard runs; a secret sits in a file with a harmless name; a broad add stages the env file (F10) | before the first commit and again before the push, the content of every file to be committed and of every commit to be pushed is scanned, by content and not by name; the ignore-file proof runs before every commit; a hit stops the run before the push with the file named and nothing shown |
| the backup | a dump holds the project's data, which can include its users' secrets | a permitted secret store (below) |

## The permitted secret stores

"No secret in any byte written" was wrong as the first draft put it (F11): the run exists to
write some secret-bearing files. These are the only ones, and each has a rule:

| File | Where | Protection |
|---|---|---|
| the pulled env file | the working tree | ignored by git (proven before every commit), owner-only |
| the database dump | the archive, beside the repo (page 3) | owner-only, outside any working tree, never printed, hash recorded |
| the saved hosting env values (ruled, contract A2: sunset saves them, every environment) | the archive, beside the repo | owner-only, never printed, key names and hash recorded |
| protected way-back records | the run directory or the archive | owner-only, referenced by hash |
| the private password file | a private folder of the run | owner-only, created exclusively, removed when the command ends, and removed by the next run's recovery if a kill left it |

A secret anywhere else is a failure. A permitted store with wider permissions is a failure.

## The hosting token

The provider module reads the token in-process (from the environment, else from the hosting tool's
credentials file: ruled by the owner, contract A2, both stay, the environment first; the file is
opened by one function, read only, and no other file of that tool is touched), registers it, makes the
request itself to the provider's fixed host, and drops it. No child process, no argument, no
environment, no file. A missing token, an expired one (401 or 403) or a missing file each end as
an `owner` operation showing the dashboard step, as v1 does; the module never tries to repair or
refresh a token.

## The connection string

Found by key name in the project's env files, read once by the provider module, and split. The
host, port, database name and user are not secrets and are passed to `pg_dump` as ordinary
parameters. The password goes into a private password file that `pg_dump` is pointed at by a path
in its minimal environment; the path is not a secret. The run never prints the string, never
stores it, and never writes it into the restore manifest; a restore reads it again from the same
place, or asks the owner when that place is gone.

A password file is still readable by the owner's own processes, as every file of his is. What the
change buys is that the secret is no longer in any process's arguments or environment, is not
inherited by anything `pg_dump` starts, and exists for seconds.

## Proving it

**An inventory first, then the matrix** (F11). Each provider module declares, in one table the
tests read: every secret source it touches, every place it writes or causes a tool to write, and
which of those are permitted stores. The matrix is built from that table, so a new write without
a row fails the suite.

- **Canaries.** Each source carries a marked canary built at run time (never a literal in a
  committed file). The scan looks for the canary whole, for each of its components, and for each
  in its percent-encoded and base64 forms.
- **What is scanned.** Not only the run directory. Every test runs in a fixture home and a fixture
  working tree, and at teardown one helper scans **every file under both**, the captured standard
  output and error, every argument and every environment the fakes recorded for themselves and for
  anything they started, every git object in the fixture repository, and every request header the
  fake HTTP host recorded. The helper knows the permitted stores: a canary there passes only with
  the right permissions; anywhere else fails.
- **Failure paths, each run as its own case.** The fake fails echoing the canary whole, in part,
  encoded, and split across two writes. The fake writes the canary to a debug log in the fixture
  home. The fake is killed mid-call (the password file must be gone after the rerun's recovery).
  The tool is missing. The token is expired. The env pull writes nothing, or half a file. The
  fake answers with a redirect. The response is malformed. The disk is full on the dump. The dump
  path is a link. An exception is raised inside the provider module with the canary in a local
  value. A debug variable is set in the session's environment.
- **The trace.** The whole sequence runs under the station trace and the trace is scanned.

What the tests cannot prove is the real providers' own behavior. The live join (slice 5) is
scanned the same way before anything from it is filed, with the real values registered and the
scan run by the script over the run directory and the working tree, so no one reads them to check.

## Questions this page leaves

1. The read of the hosting tool's credentials file: RULED (contract A2), kept, after the
   environment variable. The value takes the channel above either way.
2. When the last net (key shapes) fires on a value the run never registered: redact, record a
   `redacted-unknown` event with the sink and no value, finish the run, and say so in the summary.
   Stopping mid-sunset would strand the project. With rule 2 in place this can happen only on text
   shown on request.
3. Whether the tail of a failed command is kept at all. Reading: not by default; the error kind is
   kept, and the tail is produced on the owner's request by rerunning the read-only probe.
