# Adapter index (E9)

The portable body (`../SKILL.md`) names no harness. This index maps the harness you run in to
its adapter profile; the profile says how the `invocation` block is filled, how the verifier is
summoned, and which of those the harness enforces. Identify your harness from what it tells
you about itself (its system prompt, its tool names), never from a guess. A harness this index
does not list has no adapter: the run stops as `verifier_unavailable` with `stop_reason`
`unknown_capability: no adapter profile for <what the harness calls itself>`, and nothing is
graded.

| Harness | Profile | Helpers (each with `--help`, JSON on stdout, diagnostics on stderr) | Verifier capability |
|---|---|---|---|
| Claude Code | `claude-code/profile.md` | `claude-code/invocation.py` (the invocation facts), `claude-code/turns.py` (the user channel), `claude-code/verifier.py` (the readers request block) | the readers component: row `claude-session`, profile `repo-with-tools` |
| Codex CLI | `codex/profile.md` | `codex/invocation.py`, `codex/turns.py`, `codex/verifier.py` (launches the fresh run and prints the `record-call` flags) | one fresh `codex exec` run per call |
| OpenCode | `opencode/profile.md` | `opencode/invocation.py`, `opencode/turns.py`, `opencode/verifier.py` (launches the fresh session and prints the `record-call` flags) | one fresh `opencode run` session per call |

Every profile carries the same twelve sections in the same order (the E9 lane contract
`docs/plans/2026-09-14-recheck-v2-e9-adapters.md`, section 5): identity; model and floor; run
id and directory; the user channel; `session_wrote_fix`; run date; the verifier capability;
delivery; sidecars and invocation restrictions; negative tests; installed-package
verification; capability labels. The helpers run under Python 3.9 with the standard library
only and are resolved from this directory, never from a checkout or a cache.
