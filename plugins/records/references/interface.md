# The records component interface, version 1

What a station, a reader, or any other consumer writes against. The CLI
(`scripts/records.py`) and the four schemas beside this file are the interface; everything under
`scripts/records_core/` is internal, and a consumer that imports the library instead of calling
the CLI is outside this interface and unprotected by its version.

Written for E12 of the skills v2 rebuild, against the records E12 lane contract. Where this
document and the contract differ, the contract is the authority and this document is the defect.

## The version markers, and what each promises

Ruling E12-7 gives three independent markers a reader branches on: `v` on every event, the
finding ID prefix, and `interface_version`. `component_version` is a fourth thing entirely, and
promises nothing about the interface; it is in this table so the two are never confused.

| Marker | Where | Meaning |
|---|---|---|
| `interface_version` | every response | this document. Starts at 1. A new required argument, a removed field, or a changed meaning is a new version. |
| `component_version` | every response | the build, from `.claude-plugin/plugin.json`. `0.1.0` today. It moves when the code moves; it promises nothing about the interface. |
| `v` | every event in a log | the event schema. `1` today. A reader refuses an event whose `v` it does not know (exit 4, naming the line) rather than skipping it. |
| `f1:` | every finding ID | the identity scheme. A future scheme is `f2:`, and both can sit in one log. |

A field this document does not name is not part of interface version 1, whatever the code
returns. A test (`scripts/tests/test_interface.py`) holds the two in step in both directions:
every field the code returns is named here, and every field named here is returned by some real
run.

## Reaching the component

A station resolves the component root and then runs `<root>/scripts/records.py`. The order, from
the contract's section 12.1: the `--records-root` argument the station itself takes, then the
`RECORDS_ROOT` environment variable, then the plugin installed beside the station
(`<station plugin root>/../records`). The first that holds `scripts/records.py` wins. Nothing
found is exit 3 with

```text
missing dependency: records component (looked in: <the candidates, in order>)
```

`--records-root` and `RECORDS_ROOT` are the STATION's, not this CLI's: `records.py` is the
component and never performs this lookup. It reads no `RECORDS_ROOT`, and its own
`--component-root` flag is a test hook (see "Arguments every command takes").

Copy one of these. They are the same three lookups in the same order, and
`scripts/tests/test_resolution.py` extracts both from this file and exercises each route and the
not-found message on a real checkout.

<!-- resolver: python -->

```python
#!/usr/bin/env python3
"""Resolve the records component root (records E12 contract section 12.1).

    python3 records_root.py [--records-root DIR] [--station-plugin-root DIR]

Prints the root on stdout, or the missing-dependency line on stderr and exits 3.
"""
import os
import sys


def records_root(argument=None, station_plugin_root=None, environ=None):
    environ = os.environ if environ is None else environ
    candidates = [argument, environ.get("RECORDS_ROOT")]
    if station_plugin_root:
        candidates.append(os.path.join(station_plugin_root, os.pardir, "records"))
    looked = []
    for candidate in candidates:
        if not candidate:
            continue
        looked.append(candidate)
        if os.path.isfile(os.path.join(candidate, "scripts", "records.py")):
            return candidate
    raise LookupError("missing dependency: records component (looked in: %s)"
                      % (", ".join(looked) or "nothing given"))


if __name__ == "__main__":
    given = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    try:
        sys.stdout.write(records_root(given.get("--records-root"),
                                      given.get("--station-plugin-root")) + "\n")
    except LookupError as missing:
        sys.stderr.write("%s\n" % missing)
        sys.exit(3)
```

<!-- resolver: sh -->

```sh
# $1: the station's --records-root value, or empty. $2: the station's plugin root, or empty.
# Prints the root, or the missing-dependency line on stderr and returns 3.
records_root() {
  looked=""
  for candidate in "$1" "${RECORDS_ROOT-}" "${2:+$2/../records}"; do
    [ -n "$candidate" ] || continue
    looked="${looked:+$looked, }$candidate"
    if [ -f "$candidate/scripts/records.py" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  printf 'missing dependency: records component (looked in: %s)\n' "${looked:-nothing given}" >&2
  return 3
}
```

### What the third route measures, on the two harnesses E12 covers

Measured on 2026-09-20 by installing this component and a minimal station plugin from one local
marketplace into an isolated home under a temporary directory (never a live home, no login, no
network):

| Harness | Version | Where an installed plugin's root sits |
|---|---|---|
| Claude Code | 2.1.278 | `<config>/plugins/cache/<marketplace>/<plugin>/<version>/` |
| Codex | 0.154.0 | `<CODEX_HOME>/plugins/cache/<marketplace>/<plugin>/<version>/` |

Both harnesses keep plugins from one marketplace beside each other BY NAME, and then put each
plugin's root one directory further down, under its own version, with several versions of one
plugin able to sit there at once. `<station plugin root>/../records` is therefore
`…/<marketplace>/<station>/records`, which exists on neither harness. The third route as the
contract writes it finds nothing on an installed plugin; it resolves correctly on a checkout,
where `plugins/<station>/../records` is `plugins/records`.

How the third route should read on an installed plugin is open with the control room. No fourth
lookup was invented for it. Until it is ruled, a station reaches an installed component through
the first or second route.

## Running a command

```sh
uv run <root>/scripts/records.py <command> [arguments]
```

- `jsonschema==4.25.1` is the one dependency, declared in `records.py`'s PEP 723 block. Started
  without it, every command writes one line to stderr and exits 3, with nothing on stdout:
  `missing dependency: jsonschema==4.25.1 (run through uv run, or install it)`. `--help` and
  argument checking still work without it.
- The runtime floor is Python 3.9 (`/usr/bin/python3` 3.9.6) and git 2.50.1.
- Stdout carries one JSON document and nothing else. Diagnostics go to stderr.
- Every command is safe to run from any working directory. `--workspace` and every file argument
  are absolute or resolved from the current working directory; `--doc` is workspace-relative.
- Git runs read-only (`rev-parse`, `status`, `diff`, `ls-files`, `submodule status`, `blame`),
  and only inside the workspace given.
- Only `append` and `import-legacy` write, and only two files, both under `docs/records/` inside
  the workspace: the log, and `<log>.lock`. A pass that refuses anything writes nothing at all.
- Rerunning a read-only command is always safe. Rerunning an `append` that already landed is
  correctly a failure: its `--expect-head` no longer matches. A second `import-legacy` over an
  unchanged document appends nothing.

### Arguments every command takes

| Argument | Meaning |
|---|---|
| `--help` | arguments, defaults, an example, the side effects, and the exit codes. Works without `jsonschema`. |
| `--component-root DIR` | TEST ONLY, and before the command name. Reads this component's references and computes its identity from `DIR` instead of from the script's own location. It is not section 12.1's `--records-root`; a station never passes it. |

`--workspace W` is a directory, and for `identity` and `append` a git work tree root with a HEAD
commit (anything else is exit 2). `--doc D` is workspace-relative, normalized, inside the
workspace, and ends in `.md` (a build doc, or `docs/punch-list.md`); anything else is exit 2.
The document itself need not exist for the commands that only read a log.

Two environment variables are honoured, both test hooks and both ignored unless `RECORDS_TEST=1`
is also set: `RECORDS_TEST_NO_JSONSCHEMA=1` behaves as if `jsonschema` were not importable.

## Exit codes

| Code | Name | Means |
|---|---|---|
| 0 | success | the response carries `ok: true`. |
| 1 | anything else | an unsupported workspace (a submodule), a git failure, a file system refusal, a defect of the script. A submodule refusal carries a JSON body; a git or file system failure reports on stderr and prints nothing. |
| 2 | usage | a missing or malformed argument, a file that is not there, a `--doc` outside the workspace. Reported by the argument parser on stderr; stdout is empty. |
| 3 | missing dependency | `jsonschema` did not import. One line on stderr, nothing on stdout. |
| 4 | validation | an input, an event, or a log line failed validation. `error: "invalid"`. |
| 5 | ambiguous identity | section 7's identity cases, and section 11.5's ambiguous legacy lines. `error: "ambiguous_identity"`. The response explains every case. |
| 6 | stale source | a clear against a source that is not the workspace, or against a finding that is not open. `error: "stale_source"`. |
| 7 | conflict | a chain break, a head mismatch, a held lock, or a legacy document whose imported record lines changed or moved. `error: "conflict"`. |

0 to 4 are the A7a meanings; 5, 6 and 7 are this component's. Every non-zero exit that carries a
body carries `ok: false`, `error`, and `reason`, and writes nothing.

## Addresses

Specification and operational history are separately addressable, and neither reaches the other:

- `spec` is `{"doc": D, "slice": "<name>" | null}` — the ledger document and, where one applies,
  the slice heading. The specification is never copied into a log.
- `history` is `{"log": "<log path>", "seq": n}` — one event.

For a ledger document at workspace-relative path `D`, the log is
`docs/records/<slug>.events.jsonl`, where `<slug>` is `D` with its `.md` removed and every `/`
replaced by `__`: `docs/plans/2026-09-06-readers.md` gives
`docs/records/docs__plans__2026-09-06-readers.events.jsonl`. Every response reports `log` as that
workspace-relative path, so an address is portable between machines.

The log is UTF-8, one canonical JSON object per line (sorted keys, no insignificant whitespace,
`ensure_ascii` false), LF endings, one trailing newline. It is a tracked file.

## Every response

| Field | Meaning |
|---|---|
| `ok` | true on success, false on every refusal. One switch beside the exit code. |
| `interface_version` | this document's version, `1`. |
| `component_version` | the build, from `plugin.json`. |

## Every command that walks a log

`verify`, `events`, `append`, `state`, `render` and `import-legacy` read the log before they do
anything else, so each of them can answer with the walk's own refusals: exit 4 when a line does
not parse, carries an unknown `v`, or fails the event schema, and exit 7 when `seq` is not the
line index or `prev` is not the hash of the line before.

| Field | Meaning |
|---|---|
| `error` | `invalid`, `ambiguous_identity`, `stale_source`, `conflict`, or `unsupported`. |
| `reason` | one sentence naming what failed, where, and what the caller can do. |
| `line` | the 1-based line of the log, or of the legacy document, the refusal is about. |
| `seq` | the `seq` the offending line carries. |
| `expected_seq` | the `seq` its position requires. |
| `errors` | the validation findings, in path order. |
| `errors[]` | one finding. |
| `errors[].path` | a JSON pointer into the event or the input. |
| `errors[].message` | what the schema, or one of the two semantic rules, said. |

## Every command that takes the lock

`append` and `import-legacy` are the two commands that write, and each holds `<log>.lock` while
it does. The lock file is created with exclusive creation and holds the pid, that process's start
time, and the command; a lock that exists is exit 7 with its contents, and `--break-lock` removes
one only when its pid is not alive. There is no waiting and no retry loop. A process killed
between taking the lock and releasing it leaves the lock behind, which is the one partial effect
either command has; `import-legacy --dry-run` takes no lock at all.

| Field | Meaning |
|---|---|
| `lock` | the lock that is in the way, on exit 7. |
| `lock.pid` | its pid. |
| `lock.pid_start` | its holder's start time, as recorded when it was taken. |
| `lock.command` | the command that took it. |
| `lock.unreadable` | why the lock file could not be read, when it could not. |
| `lock_path` | the lock file's absolute path. |
| `holder_alive` | is the process that took the lock still running: the pid AND its recorded start time, because a recycled pid is not the holder. |
| `broke_lock` | the stale lock this run removed, when `--break-lock` did something. |
| `broke_lock.pid` | the pid it recorded. |
| `broke_lock.pid_start` | that process's start time as recorded. |
| `broke_lock.command` | the command that took it. |

## The commands

### `verify`

`verify --workspace W --doc D` walks the chain and the schema of one document's log and writes
nothing. A log that does not exist yet verifies clean: `exists: false`, `head` 64 zeros, `events`
0, exit 0.

| Field | Meaning |
|---|---|
| `exists` | is there a log file at all. |
| `log` | the log's workspace-relative path. |
| `head` | the SHA-256 of the last line's bytes without its newline; 64 zeros for a log with no lines. |
| `events` | how many events the log holds. |
| `spec` | the specification address. |
| `spec.doc` | the ledger document. |
| `spec.slice` | the slice, or null. |

### `events`

`events --workspace W --doc D [--finding ID] [--kind K] [--from N]` prints the log's events in
`seq` order, each with its two addresses, and writes nothing. The chain is walked first, so a
broken log is refused rather than read. The three filters are and-ed; `--from` is inclusive.

| Field | Meaning |
|---|---|
| `log` | the log's workspace-relative path. |
| `head` | the hash of the last line. |
| `events` | how many events the log holds, before filtering. |
| `exists` | is there a log file at all. |
| `spec` | the specification address of the document. |
| `spec.doc` | the ledger document. |
| `spec.slice` | null at this level. |
| `filters` | the filters as they were applied. |
| `filters.finding` | the `--finding` value, or null. |
| `filters.kind` | the `--kind` value, or null. |
| `filters.from` | the `--from` value, or null. |
| `returned` | how many events passed the filters. |
| `results` | the events that passed, in `seq` order. |
| `results[]` | one event with its addresses. |
| `results[].seq` | its position in the log. |
| `results[].event` | the event itself. |
| `results[].event.*` | one event line, exactly as the log holds it; `references/event.schema.json` is its description, and this document does not repeat it. |
| `results[].history` | the history address of this event. |
| `results[].history.log` | the log's path. |
| `results[].history.seq` | the event's `seq`. |
| `results[].spec` | the specification address this event points at. |
| `results[].spec.doc` | the ledger document. |
| `results[].spec.slice` | the event's slice, or null. |

### `identity`

`identity --workspace W` prints the six-field source identity of the workspace and writes
nothing. The log and everything else under `docs/records/` is excluded from the dirty check, the
tracked diff and the untracked list, so appending to a log does not change the identity of the
source that log describes. The exclusion list is fixed: `docs/records/`.

A workspace with an initialized submodule is refused the way the pilot refuses it, exit 1
`unsupported`: a submodule's working contents can change without its pinned commit changing, so
the six fields would not describe the tree. A workspace that is not a git work tree root, or has
no HEAD commit, is exit 2.

| Field | Meaning |
|---|---|
| `workspace` | the absolute path the identity was computed in. |
| `identity` | the six fields. |
| `identity.commit` | the 40-hex commit at HEAD. |
| `identity.dirty` | is the tracked tree different from that commit. |
| `identity.tracked_diff_sha256` | SHA-256 of the tracked diff, or 64 zeros when it is empty. |
| `identity.untracked` | the untracked paths, sorted. |
| `identity.untracked_sha256` | SHA-256 over those paths and their contents. |
| `identity.submodules` | the initialized submodules; a workspace with any is refused. |
| `excluded` | what was left out of the three checks above. |
| `excluded[]` | one excluded prefix: `docs/records/`. |
| `error` | `unsupported`, on the submodule refusal. |
| `reason` | `unsupported: submodules: <paths>`. |
| `submodules` | the submodules that caused the refusal. |
| `submodules[]` | one submodule path. |

### `append`

`append --workspace W --doc D --events FILE --expect-head H [--break-lock]` appends one or more
events to a log, all or none, and is the one writing command a station calls.

- `--events` is a JSON file holding an array of events, or one event object. `seq` and `prev` are
  assigned by the component, never by the caller: an event carrying either is exit 4. The finding
  ID of a `finding_raised` or `defect_raised` is likewise computed from the event's own fields; a
  supplied `finding` that is not the computed one is exit 4, and an absent one is filled in.
- `--expect-head` is the hash of the last line the caller read, or 64 zeros for a log that does
  not exist yet. A different head on disk is exit 7 with both heads, and nothing is written. The
  component never merges for the caller.
- `--break-lock` removes a `<log>.lock` whose pid is not alive and says so in the response. A
  lock whose holder is alive is exit 7. There is no waiting and no retry loop.
- A `disposition` with `disposition: "fixed"`, and a `waived`, are refused (exit 6) unless the
  event carries `verified_source` with `known: true`, that identity equals the one computed in
  the workspace field for field, and the finding it names is open at the log's current head.
- Native events only. An event carrying `origin.kind: "legacy"`, or the importer's station
  `records-import`, is refused (exit 4) before anything else about it is judged. A legacy record
  enters a log only through `import-legacy`, which reads it from the document itself.

| Field | Meaning |
|---|---|
| `log` | the log's workspace-relative path. |
| `head` | the hash of the last line after the append, or before it on a refusal. |
| `events` | how many events the log holds after the append, or before it on a refusal. |
| `spec` | the specification address of the document. |
| `spec.doc` | the ledger document. |
| `spec.slice` | null at this level. |
| `expected_head` | the `--expect-head` the caller gave. |
| `actual_head` | the head on disk, on a head mismatch. |
| `appended` | one row per event written, in order. |
| `appended[]` | one written event. |
| `appended[].seq` | the `seq` the component assigned. |
| `appended[].kind` | the event's kind. |
| `appended[].finding` | the finding it names, or null. |
| `appended[].history` | its history address. |
| `appended[].history.log` | the log's path. |
| `appended[].history.seq` | its `seq`. |
| `event_index` | the 1-based position in `--events` of the event that was refused. |
| `path` | the JSON pointer of the field a section 7 refusal is about. |
| `finding` | the finding ID the refused event names. |
| `candidates` | where the log already holds that identity. |
| `candidates[]` | one history address. |
| `candidates[].log` | the log's path. |
| `candidates[].seq` | the `seq` of the event that holds it. |
| `condition` | which of section 8.3's three conditions failed: `known`, `identity`, or `open`. |
| `differing_fields` | which of the six identity fields differ. |
| `differing_fields[]` | one field name. |
| `expected` | the identity the event was decided against. |
| `expected.*` | the six identity fields, the same shape `identity` returns; null when the event supplied none. |
| `actual` | the identity computed in the workspace now. |
| `actual.*` | the six identity fields. |

### `state`

`state --workspace W --doc D [--at-source F] [--slice S]` prints the derived state of one log and
writes nothing. State is a pure function of the log's bytes: the same log gives the same object,
byte for byte, on any machine, and nothing here reads the document or the clock.

The deciding event of a finding is the last event in `seq` order that names it among
`disposition`, `waived` and `reopened`; none means open. That is Appendix A's "later in the file
wins" with the finding ID as the join key.

`--at-source F` names a JSON file holding a six-field identity, or a response carrying one under
`identity`. It changes no state; it adds `cleared_at_this_source` per cleared finding, true only
when the clear was bound and names that commit.

`--slice S` filters both the findings and the slices to one slice.

| Field | Meaning |
|---|---|
| `log` | the log's workspace-relative path. |
| `head` | the hash of the last line. |
| `events` | how many events the log holds. |
| `exists` | is there a log file at all. |
| `spec` | the specification address, carrying the `--slice` when one was given. |
| `spec.doc` | the ledger document. |
| `spec.slice` | the slice filtered to, or null. |
| `filters` | the filters as they were applied. |
| `filters.slice` | the `--slice` value, or null. |
| `at_source` | what `--at-source` compared against, or null. |
| `at_source.commit` | that identity's commit. |
| `open` | how many findings are open, by severity, after the filter. |
| `open.BLOCKER` | open BLOCKERs. |
| `open.MAJOR` | open MAJORs. |
| `open.MINOR` | open MINORs. |
| `counts` | totals over the findings returned. |
| `counts.findings` | how many findings. |
| `counts.open` | how many are open. |
| `counts.fixed` | how many are fixed. |
| `counts.waived` | how many are waived. |
| `counts.cleared_unbound` | how many were cleared against no known source. |
| `findings` | one row per finding, in the order they were raised. |
| `findings[]` | one finding. |
| `findings[].id` | the `f1:` finding ID. |
| `findings[].slice` | the slice it is charged to, or null. |
| `findings[].severity` | BLOCKER, MAJOR or MINOR. |
| `findings[].location` | the location as the raise recorded it. |
| `findings[].location.raw` | the field exactly as written. |
| `findings[].location.file` | the file, or null when the field names none. |
| `findings[].location.line` | the line, or null. |
| `findings[].location.line_end` | the end of a range, or null. |
| `findings[].location.tag` | a glued parenthetical tag, or null. |
| `findings[].location.more` | further locations named in the same field. |
| `findings[].location.resolved` | did the field resolve to a `file:line`. |
| `findings[].claim` | the claim, or null. |
| `findings[].scenario` | the failure scenario, or null. |
| `findings[].status` | `open`, `fixed` or `waived`. |
| `findings[].cleared_unbound` | true when the deciding clear carried no known source (owner ruling O4). |
| `findings[].join_basis` | the deciding event's join basis, or null. |
| `findings[].raised` | the history address of the raise. |
| `findings[].raised.log` | the log's path. |
| `findings[].raised.seq` | its `seq`. |
| `findings[].decided` | the history address of the deciding event, or null. |
| `findings[].decided.log` | the log's path. |
| `findings[].decided.seq` | its `seq`. |
| `findings[].events` | every `seq` that names this finding. |
| `findings[].events[]` | one `seq`. |
| `findings[].raised_by` | the `raised_by` field of the raise, or null. |
| `findings[].caused_by` | for a defect, the finding whose fix introduced it, or null. |
| `findings[].cleared_at_this_source` | present only with `--at-source`: was this clear bound to that commit. |
| `slices` | one row per slice, in the pilot's slice order. |
| `slices[]` | one slice. |
| `slices[].name` | the slice name, or `none`. |
| `slices[].open` | what is open for it, by severity. |
| `slices[].open.BLOCKER` | open BLOCKERs. |
| `slices[].open.MAJOR` | open MAJORs. |
| `slices[].open.MINOR` | open MINORs. |
| `slices[].open_total` | the three added up. |
| `slices[].card_derived` | Appendix A's mapping over what is open: any BLOCKER open gives `rejected`; else any MAJOR open gives `signed off with conditions`; else `signed off`; a slice last observed or set at `built` keeps `built`. Null for `docs/punch-list.md`, which has no card. |
| `slices[].card_observed` | the last card observed or set: one of the pilot's six values, or `none` when the `Status:` text is not one of them. Null when nothing observed it. |
| `slices[].card_observed_text` | the `Status:` text exactly as written, which is why a slice can read `none`. |
| `slices[].card_drift` | true when both cards exist and differ. The component reports drift; it never corrects a card in E12. |

### `render`

`render --workspace W --doc D --run-id R` prints the Appendix A text one run's events produce and
writes nothing. A run is named by `actor.run_id`. Its events render in `seq` order as one block
(when the run holds any `disposition` or `defect_raised`), then its waiver and reopening lines,
one standalone line each. Nothing in E12 writes that text into a document.

An event of the run that names a finding the log never raised is exit 4: a log that an `append`
wrote cannot hold one, but a git merge that joined two tails can, and the component says so
rather than guessing.

| Field | Meaning |
|---|---|
| `log` | the log's workspace-relative path. |
| `head` | the hash of the last line. |
| `events` | how many events the log holds. |
| `exists` | is there a log file at all. |
| `spec` | the specification address. |
| `spec.doc` | the ledger document. |
| `spec.slice` | the one slice the block names, or null when it names several or none. |
| `run_id` | the run that was rendered. |
| `date` | the date the block heading carries, or null when the run rendered nothing. |
| `slices` | the heading's slices, in the pilot's order. |
| `slices[]` | one slice name. |
| `block` | the block text: a blank line, the heading, then one line per event. Empty when the run wrote no block line. |
| `lines` | the block's lines, without the heading. |
| `lines[]` | one recheck or defect line. |
| `grants` | the standalone waiver and reopening lines, each with its newline. |
| `text` | what a station would append: the block, then the grants. |
| `rendered` | how many lines were produced. |
| `skipped` | every event of the run that carries no Appendix A line, so "nothing to render" is not confused with "I dropped something". |
| `skipped[]` | one skipped event. |
| `skipped[].seq` | its `seq`. |
| `skipped[].kind` | its kind. |
| `error` | `invalid`, on the refusal above. |
| `reason` | which event, and why it cannot be rendered. |

### `import-legacy`

`import-legacy --workspace W --doc D [--resolutions R] [--dry-run] [--break-lock]` reads one
ledger document and appends the events its records represent, in file order, to that document's
log. It never writes to the document, to a verdict doc, or to anything outside `docs/records/`.
`--dry-run` writes nothing, takes no lock, and reports what the pass would append.

What it produces, per line, in file order:

```text
a `Status:` line whose text is new for its slice     -> card_observed
a review finding line                                -> finding_raised
a fix-introduced defect line                         -> defect_raised
a recheck line                                       -> disposition
a `WAIVED (per user)` line                           -> waived
a `REOPENED (per user)` line                         -> reopened
a line under a record heading that fits nothing      -> legacy_unparsed
an answer from a resolutions file                    -> resolution_applied, then what it enables
```

bracketed by `import_started` and `import_finished`, and preceded by `log_opened` when the log
does not exist yet. A pass that finds no news appends nothing at all, not even a bracket.

Every imported clear keeps its effect and carries `{"known": false}`, so history is not changed;
derived state marks the finding `cleared_unbound` (owner ruling O4). An imported event's `at` is
the block heading's date, or the grant's date on a waiver or reopening line; `source` stays
unknown even when the line names a full 40-hex commit, which is recorded under
`origin.commit_named` instead, because a bare commit is not the six-field identity.

Any state-bearing line the join cannot place stops the whole document: exit 5, nothing written,
and a report listing every such line with its number, its raw text, the reason, and the candidate
findings. `--resolutions` supplies the answers, in the shape of
`references/resolutions.schema.json`. A resolution that names a line the import did not stop on,
a line whose raw text has changed, a finding the document does not raise, or an answer the
question cannot take is rejected: exit 4, nothing written.

| Field | Meaning |
|---|---|
| `report` | `import`, the discriminator of `import-report.schema.json`. |
| `log` | the log's workspace-relative path. |
| `head` | the hash of the last line. |
| `events` | how many events the log holds. |
| `doc` | the ledger document that was read. |
| `doc_sha256` | its SHA-256 when it was read. Equal before and after: the document is never written. |
| `dry_run` | was this a preview. |
| `run_id` | the run id this pass stamped on every event it wrote. |
| `lines_read` | how many lines the document holds. |
| `lines_classified` | how many of them this pass classified (record lines an earlier pass already imported are not among them; `Status:` lines always are). |
| `previously_imported` | how many RECORD lines an earlier pass of this document already recorded. |
| `blocks` | how many record blocks the document holds. |
| `slices` | how many slices it names. |
| `counts` | how many events of each kind this pass would write. |
| `counts.*` | one key per event kind the pass produced. |
| `imported` | how many events were appended; 0 on a dry run. |
| `would_import` | how many a dry run would append; null when it was not a dry run. |
| `opened_log` | did this pass write the `log_opened` event. |
| `ambiguous` | how many lines stopped the document. |
| `ambiguities` | those lines, with everything an answer needs. |
| `ambiguities[]` | one line that stopped the document. |
| `ambiguities[].line` | its 1-based line number. |
| `ambiguities[].raw` | its text, which an answer repeats so a changed line is caught. |
| `ambiguities[].reason` | why the join could not place it. |
| `ambiguities[].candidates` | the findings it might have meant. |
| `ambiguities[].candidates[]` | one candidate. |
| `ambiguities[].candidates[].finding` | its finding ID. |
| `ambiguities[].candidates[].line` | the line that raised it. |
| `ambiguities[].candidates[].slice` | the slice it is charged to. |
| `rejected_resolutions` | the answers that were refused. |
| `rejected_resolutions[]` | one refused answer. |
| `rejected_resolutions[].line` | the line it answered. |
| `rejected_resolutions[].why` | `line_not_asked`, `raw_changed`, `unknown_finding`, or `answer_does_not_fit`. |
| `rejected_resolutions[].reason` | that in one sentence. |
| `rejected_resolutions[].answer` | the answer as it was given. |
| `rejected_resolutions[].answer.line` | its line. |
| `rejected_resolutions[].answer.raw` | the text it recorded for that line. |
| `rejected_resolutions[].answer.skip` | present when the answer was a skip. |
| `rejected_resolutions[].answer.why` | the reason a skip gave. |
| `appended` | one row per event written, the same shape `append` returns. |
| `appended[]` | one written event. |
| `appended[].seq` | the `seq` the component assigned. |
| `appended[].kind` | its kind. |
| `appended[].finding` | the finding it names, or null. |
| `appended[].history` | its history address. |
| `appended[].history.log` | the log's path. |
| `appended[].history.seq` | its `seq`. |
| `spec` | the specification address. |
| `spec.doc` | the ledger document. |
| `spec.slice` | null at this level. |
| `line` | on a conflict, the document line that changed, moved, or appeared above the imported tail. |
| `imported_raw` | what an earlier pass recorded for that line. |
| `current_raw` | what it reads now. |
| `last_imported_line` | the highest line an earlier pass imported, when a new record appeared above it. |

### `mirrors`

`mirrors --workspace W --doc D` reports the verdict docs the pilot's glob associates with this
document's slices and writes nothing. Each of their blocks is `same`, `differs` or `absent`
against the ledger document, and every record a verdict doc holds that the ledger document does
not is `only_in_mirror`. A difference is reported, never repaired, never imported, and never
blocks an import: a verdict doc holds copies of blocks and is never a second source.

| Field | Meaning |
|---|---|
| `doc` | the ledger document. |
| `slices` | its slices. |
| `slices[]` | one slice name. |
| `spec` | the specification address. |
| `spec.doc` | the ledger document. |
| `spec.slice` | null at this level. |
| `counts` | the states, added up. |
| `counts.same` | verdict docs whose blocks all match. |
| `counts.differs` | verdict docs with at least one differing block. |
| `counts.absent` | verdict docs the ledger document has no block for. |
| `counts.only_in_mirror` | records held only by a verdict doc. |
| `mirrors` | one row per verdict doc found. |
| `mirrors[]` | one verdict doc. |
| `mirrors[].slice` | the slice its glob matched. |
| `mirrors[].verdict_doc` | its workspace-relative path. |
| `mirrors[].doc_sha256` | its SHA-256 when it was read. |
| `mirrors[].state` | `same`, `differs` or `absent` for the whole document. |
| `mirrors[].reason` | why a row is `absent` when no block could be compared. |
| `mirrors[].blocks` | one row per record block in it. |
| `mirrors[].blocks[]` | one block. |
| `mirrors[].blocks[].heading` | the block heading as written. |
| `mirrors[].blocks[].line` | its line in the verdict doc. |
| `mirrors[].blocks[].lines` | how many record lines it holds. |
| `mirrors[].blocks[].state` | `same`, `differs` or `absent`. |
| `mirrors[].blocks[].ledger_line` | the twin block's line in the ledger document, or null. |
| `mirrors[].blocks[].ledger_lines` | how many record lines the twin holds. |
| `mirrors[].only_in_mirror` | records this verdict doc holds and the ledger document does not. |
| `mirrors[].only_in_mirror[]` | one such record. |
| `mirrors[].only_in_mirror[].line` | its line in the verdict doc. |
| `mirrors[].only_in_mirror[].kind` | what the tolerant reader read it as. |
| `mirrors[].only_in_mirror[].raw` | its text. |

### `survey`

`survey --workspace W` walks the workspace's Markdown documents, keeps the ones carrying a
record, and reports for each the counts by record kind, the counts by join basis, and every line
that would stop an import. It imports nothing and writes nothing. A document under a
`docs/reviews/` directory is a mirror and is reported as one, never surveyed as a ledger
document; `docs/records/`, `.git`, `node_modules`, `__pycache__` and `.venv` are skipped.

| Field | Meaning |
|---|---|
| `report` | `survey`, the discriminator of `import-report.schema.json`. |
| `workspace` | the absolute path that was walked. |
| `counts` | the workspace's totals. |
| `counts.documents` | documents carrying a record. |
| `counts.ledger_documents` | of those, the ones that are ledger documents. |
| `counts.mirrors` | of those, the ones under `docs/reviews/`. |
| `counts.blocks` | record blocks in all of them. |
| `counts.records` | record lines in all of them. |
| `counts.stops` | lines that would stop an import. |
| `counts.documents_that_would_stop` | ledger documents holding at least one. |
| `documents` | one row per document, sorted by path. |
| `documents[]` | one document. |
| `documents[].doc` | its workspace-relative path. |
| `documents[].role` | `ledger` or `mirror`. |
| `documents[].doc_sha256` | its SHA-256 when it was read. |
| `documents[].lines` | how many lines it holds. |
| `documents[].blocks` | how many record blocks. |
| `documents[].slices` | how many slices it names. |
| `documents[].records` | how many record lines, by the reader's own kinds. |
| `documents[].records.*` | one key per record kind read (`finding`, `defect`, `recheck`, `waiver`, `reopening`, `unparsed`). |
| `documents[].events` | how many events an import would write. Absent for a mirror. |
| `documents[].event_counts` | those events by kind. Absent for a mirror. |
| `documents[].event_counts.*` | one key per event kind. |
| `documents[].join_basis` | how its clears would join. Empty for a mirror. |
| `documents[].join_basis.exact` | location key and claim key match exactly one finding. |
| `documents[].join_basis.location_only_no_claim` | the line carries no claim and one finding holds the location. |
| `documents[].join_basis.location_only` | one finding holds the location, its claim is worded differently, and its slice is one of the heading's (owner ruling O3). |
| `documents[].join_basis.resolved` | clears a resolutions file placed. |
| `documents[].ambiguous` | how many lines would stop an import. Null for a mirror. |
| `documents[].stops` | those lines, the same shape `import-legacy` returns. |
| `documents[].stops[]` | one line that would stop. |
| `documents[].stops[].line` | its line number. |
| `documents[].stops[].raw` | its text. |
| `documents[].stops[].reason` | why the join could not place it. |
| `documents[].stops[].candidates` | the findings it might have meant. |
| `documents[].stops[].candidates[]` | one candidate. |
| `documents[].stops[].candidates[].finding` | its finding ID. |
| `documents[].stops[].candidates[].line` | the line that raised it. |
| `documents[].stops[].candidates[].slice` | the slice it is charged to. |

### `component-identity`

`component-identity` prints what this component is and writes nothing. It takes no workspace.

| Field | Meaning |
|---|---|
| `name` | `records`, from `plugin.json`. |
| `version` | the component version, from `plugin.json`; the same value as `component_version`. |
| `commit` | the commit of the repository the component sits in, or `unversioned` outside one. |
| `content_sha256` | SHA-256 over every file under the component root (path and content), skipping `__pycache__`, `*.pyc` and `.DS_Store`. It moves when any shipped byte moves. |

## The schemas

| File | Describes |
|---|---|
| `event.schema.json` | one event line of a log. Which fields each kind requires and forbids. |
| `state.schema.json` | what `state` returns. |
| `import-report.schema.json` | what `import-legacy` and `survey` return, in three shapes told apart by `report` and `dry_run`. |
| `resolutions.schema.json` | the answers to ambiguous legacy records: an INPUT, checked before the importer reads a single answer. |

`references/examples/` holds a valid and an invalid example for every shape, and
`scripts/validate-examples.py` checks them, including a dropped-field pass over every required
field. Every object in every schema is closed (`additionalProperties: false`), so an unknown key
is refused rather than ignored.

Two rules a Draft 2020-12 schema cannot make are enforced in code, and both are part of interface
version 1: a native event's `at` must be a real calendar instant (`date-time` goes unchecked
without a format validator, so `2026-02-30T09:00:00Z` would otherwise pass), and a claim,
scenario, `how`, `words` or `raised_by` is a single line with no ` · ` in it, with one exception
below.

## Rules a reader of a log should know

- **File order is time order.** Events are ordered by `seq`, which equals the line index. A date
  or timestamp on an event is information, never an ordering key.
- **Nothing is rewritten.** The component never edits or deletes an event line and never edits a
  legacy document. A correction is a new event.
- **A finding ID is computed once**, when the finding is raised, from the document, the slice, the
  location key and the claim key, and is stored in the event. It is never recomputed from a later
  record. The location key drops backticks and a parenthetical tag glued to a `file:N` or
  `file:N-N`, so a recheck line that omits the tag still joins.
- **A legacy F2 finding keeps the separator inside its joined scenario** (contract amendment A5).
  The single-line rule governs what this component WRITES: the separator check on `scenario`
  applies to native events only. A line break is refused everywhere, and a claim, `how`, `words`
  or `raised_by` carrying the separator is refused everywhere.
- **A structured grant line is read with or without its leading `- ` bullet** (owner amendment
  A3): a `WAIVED (per user)` or `REOPENED (per user)` line counts either way, because that is how
  every one of them is written in practice. Nothing else is read without a bullet. The pilot's
  strict reader is unchanged and still requires it.
- **A `Status:` line is an observation, not a record** (owner amendment A4). It is outside both of
  section 11.7's checks: a card flipped in place, or moved because lines were written above it,
  never conflicts. Each import appends a `card_observed` for a slice only when the current text
  differs from the `value` of that slice's last `card_observed` in the log, matched by slice name
  and never by line number, or when the log holds none for that slice. A slice whose `Status:`
  line is gone appends nothing, and a pass whose only news is one flipped card appends
  `import_started`, that `card_observed`, and `import_finished`. RECORD lines keep section 11.7
  as written: one that changed, moved, or appeared above the imported tail is exit 7.
- **A clear cannot be written against another revision.** That is what exit 6 is for, and the
  importer is the one writer exempt from it, only for a legacy record, only through
  `import-legacy`, and the exemption has no flag on this CLI.
- **The chain is the conflict detector.** A git merge that joined two tails leaves the second
  tail's first `prev` naming a line that is no longer its predecessor, and `verify` names that
  line.

## What is not the interface

- `scripts/records_core/` and `fixtures/build.py`. Internal; their module boundaries can move
  inside one interface version.
- `scripts/validate-examples.py`. A check over this component's own examples, not a command a
  station calls; it is not in the table above on purpose.
- `--component-root`, `RECORDS_TEST` and `RECORDS_TEST_NO_JSONSCHEMA`. Test hooks.
- The exact wording of any `reason`. It is written for a person; branch on the exit code, on
  `error`, and on the named fields.
