# Adapter index (E13 slice 3)

The portable body (`../SKILL.md`) names no harness. This index maps the harness you run in to its
adapter profile; the profile says how the `invocation` block of `../references/input.schema.json`
is filled, which of those facts the harness enforces, and what each helper prints. Identify your
harness from what it tells you about itself (its system prompt, its tool names), never from a guess.

| Harness | Profile | Helpers (each with `--help`, JSON on stdout, diagnostics on stderr, exit 0/2/3/1) |
|---|---|---|
| Claude Code | `claude-code/profile.md` | `claude-code/invocation.py` (the invocation facts and the answer's `session_id`) |
| Codex CLI | `codex/profile.md` | `codex/invocation.py` (the same, from the executor's own rollout) |

**A harness this index does not list has no adapter** (OpenCode among them: the E13 lane contract's
pick P3 scoped this step to Claude Code and Codex). There is no invocation helper for it, so the
input cannot be built with its facts. The build core has no stop of its own for a missing adapter:
the input schema requires `invocation.harness`, `caller` and `mode`, and an input without them is
refused at `check-input` with exit 4, which is where the run ends. Say so and stop; never type the
block by hand.

No `turns.py` ships: the build core's input carries no user-channel field (its one user-word
switch, `allow_open_blocker`, is a boolean the input sets, with no turn reference), so there is
nothing for a turn map to fill. Every profile carries the pilot's twelve sections in the same order
(the E9 lane contract, section 5.1); a section that does not apply to this core says so and why.
The helpers run under Python 3.9 with the standard library only and are resolved from this
directory, never from a checkout or a cache.
