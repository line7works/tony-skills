# E16 design page 2: keeping credentials out of logs, traces and error output

Drafted 2026-10-11 by the control room, beside the E16 lane contract
(`2026-10-11-stations-e16.md`, ruling E16-7; plan amendment A8: "the script extraction tests the
tracing and error-output paths for credential exposure"). **Status: DRAFT, not read by the
reviewer yet.**

## The problem

Moving v1's commands into scripts makes a new risk. In v1 a model types a command and the secret
passes through one shell line. In v2 a script runs the command, writes a journal, keeps the
command's output for a resume, renders a preview and a tombstone from what it kept, and reports
errors. Every one of those is a place a token or a connection string can come to rest, and some of
them are files that outlive the run or get pasted into a chat. The repository is public and the
run directory is read by a model.

## The secrets a lifecycle run meets

| Secret | Where it comes from | Who needs it |
|---|---|---|
| the hosting token | an environment variable, or the hosting tool's own credentials file | the pause and unpause requests |
| the GitHub token | held by `gh` in its own store | `gh` only; the core never asks for it |
| the database connection string | a key in the project's env files, or the hosting tool's env pull | `pg_dump` |
| the pulled env file | written by the hosting tool into the working tree, about 17 keys | the project, later; the run needs only the key names |
| a key or certificate file in the working tree | the owner or a scaffolder | nobody in the run; it must never be committed |

## Where a secret can leak

Each row is a place v1 or a plain script would leak it. The right column is the rule.

| Sink | How it leaks | Rule |
|---|---|---|
| a command's arguments | v1 runs `pg_dump "<connection string>"` and `curl -H "Authorization: Bearer <token>"`; any process on the machine can read another's arguments while it runs, and a failed-command error prints them | a secret is never an argument. `pg_dump` gets its connection through its environment. The hosting request is made in-process, with no child at all |
| the journal and the manifest | recording "what I ran" or "what the provider said" | operations name secrets by a label (`host-token`, `db-url`); values never enter a record |
| kept command output | a provider echoes a connection string in an error; an env pull prints a path and a count, a verbose flag prints headers | all child output passes one redaction filter before it is stored or shown |
| error text and tracebacks | an exception message carries a URL with a password in it, or the failed command line | errors are built from the operation's label and the filtered output, never from the raw exception |
| the trace | the station trace of E15 records each visit; a lifecycle trace would record each command | the trace records the operation id and the command's name, never its environment |
| the preview, the summary, the tombstone, the restore manifest, the hand-off prompt | rendered from the journal | safe if the journal is; scanned anyway |
| the standard output the model reads | a script that "confirms the env file is non-empty" by printing it | a check on a secret-bearing file reads key names and counts only |
| a shell or tool trace flag | `set -x`, a tool's verbose or debug flag | forbidden on any command that handles a secret; the runner refuses a known flag |
| git | the pulled env file or a key file staged by a broad add | the ignore-file proof before every commit; a commit whose file list names an env file or a key file is refused |
| the backup | a dump holds the project's data, which can include its users' secrets | it is written outside the working tree with owner-only permissions and never printed (page 3) |

## The drawing

```
   secret sources                 the guard                      everything that persists or prints
 ┌────────────────┐      ┌──────────────────────────┐      ┌────────────────────────────────────┐
 │ environment     │      │ REGISTRY of live values   │      │ journal · manifest · kept output    │
 │ tool's own file │ ───► │  (in memory only)         │      │ trace · preview · summary           │
 │ project env file│      │                           │      │ tombstone · restore manifest        │
 └────────────────┘      │ RUNNER, the one way to    │ ───► │ standard output · standard error    │
                          │ start a child:            │      │ error messages                      │
                          │  · refuses a registered   │      └────────────────────────────────────┘
                          │    value in an argument   │                     ▲
                          │  · passes secrets by      │                     │
                          │    environment only       │            FILTER: every byte from a child
                          │  · captures both streams  │ ───────────────────┘  and every error text
                          └──────────────────────────┘      passes it: registered values first,
                                                             then key shapes as a second net
```

Two nets, on purpose. The registry knows the exact live values, so it catches a secret in any
form it was read in. The shape patterns catch a secret the run never registered, such as one a
provider prints that the run did not know it had. Neither replaces the first rule: a value that is
never put somewhere cannot leak from there.

## The hosting token

v1 reads the token from the environment, else from the hosting tool's credentials file, in one
shell line built so the value lives only in a variable. In v2 the provider module does that read
in-process, registers the value, makes the request itself and drops it. No child process, no
argument, no file. The file is read by one function with one caller. A missing token, an expired
one (401 or 403) or a missing file each end as an `owner` operation showing the dashboard step,
as v1 does; the module never tries to repair or refresh a token (contract Q3 asks whether the
file read stays at all).

## The connection string

Found by key name in the project's env files, read once by the provider module, registered, and
handed to `pg_dump` through its environment. The provider is told from the host name, which is
not a secret and may be shown. The run never prints the string, never stores it and never writes
it into the restore manifest; a restore reads it again from the same place, or asks the owner
when that place is gone.

## Proving it

A matrix, not a sample. Rows: each secret source above, carrying a marked canary built at run time
(never a literal in a committed file). Columns: every sink above. Cells run on the success path
and on each failure path: the provider's fake fails with the canary echoed in its error; the fake
is killed mid-call; the tool is missing; the token is expired; the env pull writes nothing; an
exception is raised inside the provider module with the canary in a local value.

A pass is: the canary appears in no byte under the run directory, in no byte of standard output or
standard error, in no rendered form, and in no argument recorded by any fake. The scan is one
helper every suite calls at teardown, so a new operation is covered without a new test. A second
check runs the whole sequence under the station trace and scans the trace.

What the tests cannot prove is the real providers' own output. The live join (slice 5) is scanned
the same way before anything from it is filed, with the real values registered and the scan run by
the script, so no one reads the run directory to check it.

## Questions this page leaves

1. Keep the read of the hosting tool's credentials file, or require the environment variable
   (contract Q3). The owner's.
2. Whether the shape net should stop the run or only redact when it fires on a value the registry
   does not know. Reading: redact, record a `redacted-unknown` event with the sink and no value,
   and finish the run, since stopping mid-sunset strands the project; the summary says it fired.
3. Whether the kept command output is kept at all after a clean run. Reading: kept, filtered,
   because a resume and a review need it.
