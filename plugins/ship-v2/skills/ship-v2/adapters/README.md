# Adapter index (E15 slice 1, the back frame)

The portable body (`../SKILL.md`) names no harness. This index maps the harness you run in to its
adapter profile; the profile says how the `invocation` block of `../references/input.schema.json`
is filled, which of those facts the harness enforces, and what each helper prints. Identify your
harness from what it tells you about itself (its system prompt, its tool names), never from a
guess.

| Harness | Profile | Helpers (each with `--help`, JSON on stdout, diagnostics on stderr, exit 0/2/3/1) |
|---|---|---|
| Claude Code | `claude-code/profile.md` | `claude-code/invocation.py` (the invocation facts and the answer's `session_id`) |
| Codex CLI | `codex/profile.md` | `codex/invocation.py` (the same, from the executor's own rollout) |

**A harness this index does not list has no adapter** (OpenCode among them: E13's pick P3 stands in
E15). There is no invocation helper for it, so the input cannot be built with its facts: the input
schema requires `invocation.harness`, `caller` and `mode`, and an input without them is refused at
`check-input` with exit 4. Say so and stop; never type the block by hand.

Every profile carries the E9 seam's twelve sections in the same order, each answered;
`tests/test_profile.py` in each adapter holds the order to the core. The helpers are precon-v2's
(`_common.py` byte for byte, `invocation.py` with this core's name; ruling E15-3), run under Python
3.9 with the standard library only, and are resolved from this directory, never from a checkout or a
cache. `ship-v2` itself is `ship-v2`.
