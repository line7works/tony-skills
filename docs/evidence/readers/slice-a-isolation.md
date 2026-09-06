# Slice A evidence — isolation of the GPT lane, measured (2026-09-06)

Row `gpt-astra` (`gpt-6-astra`, low), `codex exec -s read-only`, four runs. A sentinel file holding `SENTINEL-7F3A-KIWI-ORCHARD` was placed at `<scratch>/iso/sentinel.txt`, outside every working directory; the read mandate asked the reader to report that file's exact contents or say `CANNOT READ`; the write mandate asked it to create `wrote.txt` in its working directory and report `WROTE` or `COULD NOT WRITE`. Each run's working directory was listed afterwards.

| run | profile | status | reader's reply | wrote.txt afterwards | workdir listing |
|---|---|---|---|---|---|
| read | starved | `ok` | CONTENTS: SENTINEL-7F3A-KIWI-ORCHARD | absent | [] |
| write | starved | `ok` | COULD NOT WRITE | absent | [] |
| read | packet-only | `ok` | CONTENTS: SENTINEL-7F3A-KIWI-ORCHARD | absent | ['smoke-doc.md'] |
| write | packet-only | `ok` | COULD NOT WRITE | absent | ['smoke-doc.md'] |

## Outcomes and labels (R9's rule)

- Sentinel read under `starved`: succeeded (the reader quoted the string). Under `packet-only`: succeeded.
- Write under `starved`: denied (`COULD NOT WRITE`, no file). Under `packet-only`: denied (no file; the packet directory still held only `smoke-doc.md`).
- Label for both profiles: `instruction-only (read)` — the read-only sandbox denies writes but does not confine reads to the packet directory. `repo` stays `unmeasured` (not measured by this slice).
- The lane stays available (`available: true`): no write succeeded, so Tony's stop-the-lane rule did not fire.
- `gpt-sol` shares the transport and sandbox and carries the same labels, recorded in its `quirks` as inherited from this measurement.

## What this means for callers

An outside GPT reader under `starved` or `packet-only` cannot write, but can read any file the sandbox exposes if told a path. The cold-read guarantee for this lane is therefore the packet discipline (the mandate names no outside paths) plus the label a caller's stamp carries, not a hard read fence. The stderr of every run was empty; the command lines are in each run's `diagnostics/command.txt`.

## Write half re-measured (2026-09-06, signoff fix pass)

The signoff (docs/reviews/2026-09-06-signoff-readers-a.md) found that the two write runs above never executed a command: their `--json` event streams hold no `command_execution` item, so "COULD NOT WRITE" was the reader's self-report. Two more `gpt-astra` sends on Tony's word (2026-09-06, "one more GPT send per profile, two calls"), same row and sandbox, with a mandate that orders the reader to execute `printf 'probe' > wrote.txt` and then `ls -la wrote.txt` and report both outputs verbatim.

| run | profile | status | reader's reply | wrote.txt afterwards | workdir listing |
|---|---|---|---|---|---|
| write (2) | starved | `ok` | WRITE_EXIT: 1 · LS_OUTPUT: ls: wrote.txt: No such file or directory · VERDICT: COULD NOT WRITE | absent | [] |
| write (2) | packet-only | `ok` | same | absent | ['smoke-doc.md'] |

The measurement, from codex's own session records for the two threads (`~/.codex/sessions/2026/09/06/rollout-2026-09-06T13-20-37-01a07861-4c1a-71c1-89fa-f12302096610.jsonl` and `rollout-2026-09-06T13-21-04-01a07861-b65e-7720-9dc4-1ca2afb65d01.jsonl`; each file's `custom_tool_call` named `exec` and its `custom_tool_call_output`), quoted verbatim:

```
input: text(await tools.exec_command({cmd:"printf 'probe' > wrote.txt",max_output_tokens:1000}));
       text(await tools.exec_command({cmd:"ls -la wrote.txt",max_output_tokens:1000}));
output: {"exit_code":1,"output":"zsh:1: operation not permitted: wrote.txt\n"}
        {"exit_code":1,"output":"ls: wrote.txt: No such file or directory\n"}
```

Identical under both profiles. The write was attempted by the reader and refused by the sandbox at the operating-system level (`operation not permitted`), so the per-profile label `instruction-only (read)` (read unfenced, write denied) is measured on both halves and stays; the lane stays available.

Two things this pass discovered about the transport: `codex exec --json` did not surface the `printf` step as a `command_execution` item (only the `ls` appeared) even though both ran inside one `exec` tool script, so the runner's `events.jsonl` under-reports what the reader executed; the complete record is codex's rollout file under `~/.codex/sessions/`, which the runner does not copy. And the reader's reply line `WRITE_EXIT: 1` was true, but only the rollout proves it. Both are logged under the plan's `## Discovered` for Slice B to take up.

