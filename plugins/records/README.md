# records

The shared records component: one append-only event log per ledger document, versioned finding
IDs, source identifiers, derived state, a legacy importer, and a documented reader interface.

A ledger document is a build doc or a `docs/punch-list.md` — the Markdown that carries review
findings, recheck lines, waivers and reopenings. Until now that Markdown was both the
specification and the whole operational history. This component keeps the history in its own
file beside the documents, so the two are separately addressable: the document still says what
was asked for, and the log says what happened.

It has no `SKILL.md` and no model trigger. Stations and other consumers reach it through one
CLI and write against `references/interface.md`, which is the interface; `scripts/records_core/`
is internal.

## Status

Interface version 1, component version 0.1.0. Built in E12 of the skills v2 rebuild, in three
slices, under the lane contract the control room holds. Nothing consumes it yet: moving the
qualified `recheck-v2` pilot onto it is the first task of E13, and `plugins/recheck-v2/` is
byte-identical through E12 on purpose. Running the importer over real repositories is a separate
job, one repository at a time, after E12 closes.

## Layout

```text
.claude-plugin/plugin.json   name and version; `component-identity` reads them
README.md                    this file
references/
  interface.md               the interface: commands, arguments, responses, exit codes, versions
  event.schema.json          one event line
  state.schema.json          the derived-state object `state` returns
  import-report.schema.json  what `import-legacy` and `survey` return
  resolutions.schema.json    the answers to ambiguous legacy records
  examples/                  valid and invalid examples for every schema
scripts/
  records.py                 the one CLI
  records_core/              the library the CLI imports (internal, not the interface)
  validate-examples.py       checks every example against its schema
  tests/                     the unittest suites (standard library)
fixtures/
  legacy/                    synthetic legacy documents, one per shape family
  build.py                   the deterministic generator for the git-backed cases
```

## Reaching it from a station

A station resolves the component root and runs `<root>/scripts/records.py`. The resolution
order, the snippet to copy, and the message a station prints when it finds nothing are in
`references/interface.md` under "Reaching the component". The short form: a `--records-root`
argument, then a `RECORDS_ROOT` environment variable, then the plugin installed beside the
station; the first that holds `scripts/records.py` wins, and nothing found is exit 3.

One measurement is open with the control room. On Claude Code 2.1.278 and Codex 0.154.0, an
installed plugin's root is `<config>/plugins/cache/<marketplace>/<plugin>/<version>/`, so two
plugins from one marketplace are siblings by NAME but each sits one directory below that, under
its own version. The third route as the contract writes it therefore finds nothing on either
harness. `references/interface.md` records the measurement; how the third route should read is
the control room's to rule, and no fourth lookup was invented.

## Running it

```sh
uv run scripts/records.py --help
uv run scripts/records.py survey --workspace .
```

`jsonschema==4.25.1` is the one dependency, declared in `records.py`'s PEP 723 block and
supplied by `uv run`. Started without it, every command exits 3 with one line on stderr and
nothing on stdout; `--help` still works. The runtime floor is Python 3.9 and git 2.50.1. The
component runs git read-only, and only inside the workspace it is pointed at.

Only `append` and `import-legacy` write, and only two files, both under `docs/records/` inside
the workspace: the log and its lock. Everything else is read-only, including
`import-legacy --dry-run`.

## Tests

```sh
cd scripts
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t tests
uv run validate-examples.py
```

The suite builds every fixture into a temporary directory and removes it, writes nothing into
the repository, and needs no network. The parity suite additionally reads the recheck-v2 pilot's
modules and its E7 fixture lanes read-only, and holds this component's copied reader to the
pilot's behaviour byte for byte.
