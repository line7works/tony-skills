# inspect-v2 on Codex: setup results

Measured by the E14 control room on 2026-09-28 (slice 3c, item 3.9, owner pick P5; the owner's ruling of 2026-09-28, contract A12:
the measurement is of the manual-only probe installed beside the station, by its words and by its explicit name, and
the station's own control is read from the equality of controls `setups/manual-only.sh` proves on the installed copies).
Harness: codex-cli 0.157.0, model gpt-6-astra, headless `codex exec`, network off, per-launch child home. Worktree
commit `7f17f7b`. Evidence: the audit packet's `check-logs/s3c-live/inspect-v2/codex/` (the rollouts, the final answers, the
launch records; the isolated homes and their copied credential are not filed).

## Install and the manual-only controls (`setups/manual-only.sh codex --home H --credential`)

Exit 0: the core installed by its own `install.sh` (the credential copied into the isolated home by the installer
itself) and verified; the probe installed beside it from a second marketplace in the same home; both installed copies
carry `disable-model-invocation: true` and `allow_implicit_invocation: false`; both prompts present. No prompt sent
by this step.

## Manual-only probe (ruling E9-5, P5): the live measurement

| Route | Record-derived outcome |
|---|---|
| asked in words (`prompts/manual-only-words.md`) | **ignored**: absent from the catalog; the model searched the disk and read the probe's `SKILL.md` out of the home's plugin cache; answered `PROBE-RAN` |
| `$manual-only-probe` (`prompts/manual-only-explicit.md`) | **ran by file read**: no catalog recognition; the same disk search then a `cat` of the probe's `SKILL.md`; answered `PROBE-RAN` |

From `rollout.jsonl` of each session: the skill catalog (`host_skills`) names no `manual-only` entry in either
session (the sidecar prevented catalog activation); the words session's shell commands search for `SKILL.md` and
`*probe*` over the workspace and the isolated home, then `cat` the probe's `SKILL.md` from
`plugins/cache/inspect-v2-probes/manual-only-probe/...`; the explicit session does the same. `final.md` is `PROBE-RAN` in
both. Sessions: `01a0eab9-e87f-76b1-94aa-912078bbe617` (words),
`01a0eaba-5d76-7f80-9753-c3fcdb2daa7b` (explicit).

E9-5's label holds on 0.157.0 exactly as measured on 0.154.0 for recheck-v2: **prevents catalog activation; does not
stop a model that reads the file**. By the pass rule in `setups/_fixtures/README.md`, the words run is recorded as
ignored, never as a pass. The station itself was not called by any prompt (the owner's ruling A12); its controls are
the probe's, byte for byte, proved on the installed copies.
