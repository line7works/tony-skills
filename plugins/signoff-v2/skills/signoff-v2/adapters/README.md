# Adapter index (E13 slice 3)

The portable body (`../SKILL.md`) names no harness. This index maps the harness you run in to its
adapter profile; the profile says how the `invocation` block of `../references/input.schema.json`
is filled, how the independent reviewer is summoned (Step 3), and which of those the harness
enforces. Identify your harness from what it tells you about itself, never from a guess.

| Harness | Profile | Helpers (each with `--help`, JSON on stdout, diagnostics on stderr, exit 0/2/3/1) | Reviewer capability |
|---|---|---|---|
| Claude Code | `claude-code/profile.md` | `claude-code/invocation.py` (the invocation facts), `claude-code/reviewer.py` (the readers request block; the sidecar map) | the readers component: row `claude-session`, profile `repo-with-tools` |
| Codex CLI | `codex/profile.md` | `codex/invocation.py`, `codex/reviewer.py` (launches the fresh reviewer and prints the answer's reviewer identity and the `record-answer` flags) | one fresh `codex exec` run per call |

**A harness this index does not list has no adapter** (OpenCode among them: pick P3). Its facts
cannot be supplied, and the core's own stop applies: the schema requires `invocation.mode`,
`caller`, `run_id`, `run_dir` and `sessions.reviewing`, so an input built without them is refused
at `check-input` (exit 4), and a model floor this run cannot establish is v1 Step 0's stop. Say so
and stop; never type the block by hand, and never review without a fresh reviewer.

No `turns.py` ships: the signoff core's input carries no user-channel field, and the gate a user
may collapse ("sign off and work any MAJORs") is SKILL.md's instruction to the executor, not an
input field the core reads. Every profile carries the pilot's twelve sections in the same order (the
E9 lane contract, section 5.1). The helpers run under Python 3.9 with the standard library only and
are resolved from this directory, never from a checkout or a cache. The core itself never launches
a harness: only `codex/reviewer.py` starts a fresh context, as the pilot's Codex `verifier.py` does.
