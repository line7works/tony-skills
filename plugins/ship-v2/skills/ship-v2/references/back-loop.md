# The back loop: the discipline the three back cores share (E15 slice 1, the back frame)

This file is identical, byte for byte, in `vertical-v2`, `handoff-v2` and `ship-v2`
(`references/back-files.txt` lists it; `scripts/tests/test_back_equal.py` holds it equal). It states
what every back core does the same way, on the E14 station loop's discipline. What a phase reads,
decides and writes belongs to one core and lives in that core's own contract under `references/`.
The four front cores' frame (their `station-loop.md` and `shared-files.txt`) is theirs and is not
changed by this one (ruling E15-3).

Contents: 1 The cores · 2 The CLI and the exit codes · 3 The input · 4 The result · 5 Report-only ·
6 The stop vocabulary · 7 The trace · 8 The records component · 9 The rules · 10 The shared code ·
11 What this file never does.

## 1. The cores

Three stations run after a slice is built: `vertical-v2` (the whole-build review), `handoff-v2` (the
end-of-slice photograph) and `ship-v2` (the coordinator). Each is a portable core: a `SKILL.md`
procedure, its own contract, schemas and examples under `references/`, one phase driver
`scripts/<station>.py` over the shared libraries `scripts/station_core/` (copied from the E14 frame)
and `scripts/back_core/` (new in E15), adapters for Claude Code and Codex, setups, and seeded cases.
Each core's phases are its own and are stated in its contract, in order; `identity` and
`skill-identity` answer at any time and belong to no run.

The executor is the model running the core's `SKILL.md`. It talks to the owner, summons readers,
visits stations, judges, and hands its judgment to the script. The script does everything that is
deterministic: it validates, finds, reads, computes, builds, renders, writes and records. It never
judges code, a finding, a slice or the wisdom of a next move (ruling E15-4).

## 2. The CLI and the exit codes

`scripts/<station>.py`, run through `uv run` (the PEP 723 block supplies `jsonschema==4.25.1`).
stdout carries one JSON document and nothing else; stderr carries diagnostics. Every response
carries `interface_version` (1), `plugin_version` (from `.claude-plugin/plugin.json`) and `station`.
Every command passes through the E14 driver's checked dispatch, so a handler that writes outside its
JSON document, or emits one without the envelope, is a defect (exit 1).

| Exit | Meaning |
|---|---|
| 0 | the command did its work; an intermediate phase has more to do |
| 1 | anything else: a defect of the script, an unreadable run directory |
| 2 | usage: a missing or malformed argument, a file that is not there or not JSON, a phase command against the wrong phase |
| 3 | missing dependency: `jsonschema` did not import, or the records component or readers is missing or speaks another interface version. One line on stderr, nothing on stdout |
| 4 | validation: a supplied file failed its schema. Nothing is written and the run stays where it was |
| 5 | refused: an answer, a request or an input a rule of the core refuses on its content. Nothing is written and the run stays where it was, so a corrected one can be offered |
| 10 | the run reached a terminal status, a completion or a stop alike |

`--help` and every argument check work without `jsonschema`. Test hooks are honored only when
`<PREFIX>_TEST=1` is set, `<PREFIX>` being the core's name upper-cased with `-` as `_`
(`VERTICAL_V2`, `HANDOFF_V2`, `SHIP_V2`): `<PREFIX>_TEST_NO_JSONSCHEMA=1` behaves as if `jsonschema`
were not importable, and `<PREFIX>_TEST_NO_RECORDS=1` as if no records component were installed.

A phase the core's hand-back has not built yet answers `phase-not-built` (exit 10) and reads and
writes nothing, the E14 frame's way.

## 3. The input

One validated input document per run, `references/input.schema.json`, closed at every level, with
valid and invalid examples beside it once the core is built. The shared
fields: `input_version` (1), `run_id` (single-use, one path segment), `workspace` (an absolute git
work tree root), `run_dir` (absolute, outside the workspace), `report_only` (default false),
`invocation` (`harness`, `caller`, `mode`, `session_id`, filled by the adapter's `invocation.py`,
never typed), and `station`, the core's own fields. The owner's words a core needs (a collapsed gate,
an order, a waiver) arrive as data in `station` or in a recorded answer, verbatim, never remembered
between runs. Caller values arrive as data, argv items or files, and are never pasted into shell text.

## 4. The result

One result document per run, the core's result schema under its references, validated with the E14 semantic checks
(`scripts/validate-result.py`: S1 a stop carries a tag and a reason and a completion carries no tag;
S2 a report-only run writes nothing outside its run directory and says so; S3 `wrote_nothing` is true
exactly when no write lies outside the run directory; S4 a write under the run directory is a
`run_artifact`). Every run ends in a terminal status, every stop included, with the trace's path.

## 5. Report-only

Every core takes `report_only`. In that mode the run writes nothing to the workspace and nothing to
the records log; its own artifacts in the run directory are the only writes, and its result says
`wrote_nothing: true`. A report-only run still reads, computes and checks, so what it would have
written is reported, not written.

## 6. The stop vocabulary

A stop is `status: stopped` with one tag. The shared tags, used by every back core for these
situations and for nothing else: `phase-not-built` (the frame's placeholder), `selection-none` (the
hunt found nothing; the run stops and asks), `selection-several` (the hunt found several candidates;
they are listed for the owner, never picked), `records-refused` (the records component refused a
call; its own sentence is carried), `station-refused` (a station or component whose identity is not
the expected v2 sibling, refused before the visit; section 7). Each core adds its own tags in its
contract and never reuses a shared tag for another meaning.

## 7. The trace

Every run of `vertical-v2` and `ship-v2` writes `trace.jsonl` in its run directory (ruling E15-7),
through `scripts/back_core/trace.py`; a line is `references/trace.schema.json`, closed at every level,
and `scripts/validate-trace.py` checks a whole file. One line per station visit or reader summons:

| Field | What it is |
|---|---|
| `kind` | `visit` (a station run), `summons` (a reader call), `refused` (a station refused before the visit) |
| `caller` | the back core that wrote the line |
| `expected` | the name the caller expected: a `-v2` station, or `readers` |
| `identity` | `name`, `version`, `root`, `interface_version`, `commit`, `content_sha256` as the station's own CLI returned them before the visit (null only on a refused line that could not read one) |
| `route` | how the root was resolved: `3a` the checkout sibling, `3b` the installed shape, `argument` a test hook |
| `run_dir` | the run directory the visit used |
| `status` | the terminal status the station or readers reported (visit and summons) |
| `call_id`, `row` | the readers call (summons only) |
| `refusal` | the rules broken and a sentence (refused only) |

**The refusal rule.** A station is refused before the visit, and the refusal is a trace line, when its
name is a v1 station's name or lacks `-v2` where a v2 station is expected (`v1-name`), when it is not
the name expected (`name-mismatch`), when its root sits under a v1 plugin folder (`v1-root`: the
checkout shape, a `plugins` folder holding the v1 name; the installed shape, the v1 name over a
version folder; or a root named for a v1 station), when its interface version is not one the caller
knows (`unknown-interface`), or when no identity could be read (`no-identity`). The ten v1 names are
the seven E14 names and the three back-half names (vertical, handoff, ship). The trace module writes
and reads the file; it never resolves, launches or reads a station itself (ruling E15-4).

## 8. The records component

A back core reaches the records component through the resolver snippet and the CLI only
(`scripts/station_core/records_client.py`, `scripts/station_core/records_link.py`), confirms
`interface_version` 2 through `component-identity`, and stops with exit 3 and a plain message when
the component is missing or speaks another version. It never opens a log file and never imports
`records_core`. What each core reads and the events it may write are ruling E15-9's and its contract's:
`vertical-v2` reads `state` and writes no event.

## 9. The rules

1. **E15-4, the executor decides, the script records.** What the executor or a reader concluded is
   recorded with who concluded it.
2. **E15-1, behavior is kept.** No core changes what its v1 station decides; what moved is where the
   deterministic half lives and how a station is reached.
3. **E15-6, no v1 at run time.** A core never reads a v1 skill's files, never shells to one, and never
   defers to one as law; `scripts/tests/test_no_v1_import.py` (the E14 test, its needle list widened to
   the three back-half names) fails when it does. A v2 sibling is resolved the records way (route 3a,
   then 3b) by `scripts/station_core/sibling.py`, never by a personal path.
4. **E15-11, the load-bearing forms do not move.** A v1 form a core renders keeps v1's bytes, dashes
   included, rendered and parsed by one module with a round-trip test; each such form is named in the
   core's contract as the exception to the no-dash rule.
5. **The gate.** Every core ends by reading back and stopping. No core pushes, merges, opens a pull
   request or runs a git command that changes a branch, an index or a worktree.

## 10. The shared code

`references/back-files.txt` lists every file identical in the three back cores, each with the source
of its bytes: copied byte for byte from `precon-v2` (the E14 helpers, the guard and the setups), or new
in E15 with `vertical-v2` as the canonical copy. A builder that needs a copied file to change stops and
asks: the change would reach the four E14 cores, which ruling E15-2 freezes.

| Module | Job |
|---|---|
| `back_core/backdriver.py` | the core's phase table over the E14 driver's seams: the parser, `check-input`, the checked dispatch, `identity`, `skill-identity`, `phase-not-built` |
| `back_core/trace.py` | the station trace: the line shapes, the refusal rule, append and read |
| `station_core/*` | the E14 helpers, unchanged: the run, the input rules, schemas, the hunt, the forms, the sibling and roster lookups, the readers request, the records client |

## 11. What this file never does

It never names a v1 station's file as a place to read, never defers to another skill's text as law,
never states one core's own decisions, and never publishes, launches a harness, calls a model or
touches the network from a script.
