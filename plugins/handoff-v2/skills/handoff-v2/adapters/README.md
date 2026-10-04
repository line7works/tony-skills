# Adapter index (E15 slice 1, handoff-v2)

The portable body (`../SKILL.md`) names no harness. This index maps the harness you run in to its adapter profile;
the profile says how the `invocation` block of `../references/input.schema.json` is filled, which of those facts the
harness enforces, what each helper prints, and the one seam v1 held in a harness tool: the memory pointer. Identify
your harness from what it tells you about itself (its system prompt, its tool names), never from a guess.

| Harness | Profile | Helpers (each with `--help`, JSON on stdout, diagnostics on stderr) |
|---|---|---|
| Claude Code | `claude-code/profile.md` | `claude-code/invocation.py` (the invocation facts and the answer's `session_id`); `claude-code/pointer.py` (the memory pointer, under the folder you give it: exit 0, 2, 5) |
| Codex CLI | `codex/profile.md` | `codex/invocation.py` (the same, from the executor's own rollout); no pointer helper: on Codex no memory pointer is written, the block in the build doc is the pointer (E15-12) |

**A harness this index does not list has no adapter** (OpenCode among them: E13's pick P3 stands in E15). There is
no invocation helper for it, so the input cannot be built with its facts: the input schema requires
`invocation.harness`, `caller` and `mode`, and an input without them is refused at `check-input` with exit 4. Say so
and stop; never type the block by hand.

Every profile carries the E9 seam's twelve sections in the same order, each answered; `tests/test_profile.py` in
each adapter holds the order to the core. The invocation helpers are precon-v2's (`_common.py` byte for byte,
`invocation.py` with this core's name; ruling E15-3); `pointer.py` is this core's own. All run under Python 3.9 with
the standard library only, and are resolved from this directory, never from a checkout or a cache. `handoff-v2`
itself is `handoff-v2`.
