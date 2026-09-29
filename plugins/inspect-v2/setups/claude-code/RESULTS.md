# inspect-v2 on Claude Code: setup results

Measured by the E14 control room on 2026-09-28 (slice 3c, item 3.9, owner pick P5; the owner's ruling of 2026-09-28, contract A12:
the measurement is of the manual-only probe installed beside the station, by its words and by its explicit name, and
the station's own control is read from the equality of controls `setups/manual-only.sh` proves on the installed copies).
Harness: Claude Code 2.1.284. Worktree commit `7f17f7b`. Evidence: the audit packet's `check-logs/s3c-live/inspect-v2/claude-code/`.

## Install and the manual-only controls (`setups/manual-only.sh claude-code --home H`)

Exit 0: the core installed by its own `install.sh` and verified by `verify-install.sh`; the probe installed beside it
from a second marketplace in the same isolated home; both installed copies carry `disable-model-invocation: true` and
`allow_implicit_invocation: false`; both prompts present. No prompt sent by this step.

## Manual-only probe (ruling E9-5, P5): the live measurement

| Route | Outcome |
|---|---|
| asked in words (`prompts/manual-only-words.txt`) | **not measured**: the session ended before a model turn |
| `/manual-only-probe` (`prompts/manual-only-explicit.txt`) | **not measured**: the same |

The harness's own message, from `result.txt` of both sessions, verbatim:

```
Not logged in · Please run /login
```

`launch.json`: `ok: false`, `claude_exit: 1`, problems "the claude process exited 1" and "the session produced no
usable result: 'Not logged in · Please run /login'"; sessions `f938019a-ec44-4495-bc12-dd5c1128bec8` (words) and `5aa24d5c-7f19-4822-a051-df5fb05a9a6c` (explicit); cost 0. The
ISOLATED config directory has no sign-in (the pilot's finding on 2.1.270, held on 2.1.280 by build-v2 and signoff-v2,
holds on 2.1.284). Not retried; never moved to the machine's own config directory. By the pass rule in
`setups/_fixtures/README.md`, a session with no model turn is not measured, never a pass.

The standing evidence for the controls on this harness is E9's measurement of the byte-identical probe on the pilot
(recheck-v2's `setups/claude-code/RESULTS.md`: asked in words, prevented activation, harness-enforced; the explicit
slash route ran it). What this measurement adds: the probe and the station install beside each other in an isolated
home on 2.1.284 with both controls in place, proved from the installed copies.
