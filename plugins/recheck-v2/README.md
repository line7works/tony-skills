# recheck-v2 (pilot)

The portable recheck pilot from the skills v2 execution plan
(`~/ObsidianVault/03-projects/tony-skills/skills-v2-execution-plan.md`). One closed-checklist
re-inspection skill meant to run as a native entry point on Claude Code, Codex, and the
OpenRouter lane, from one shared core with a small adapter per harness.

Status: **E6, contract only.** No `SKILL.md`, no scripts, no adapters yet; the plugin is not
listed in `.claude-plugin/marketplace.json` and nothing loads it. E7 adds fixtures and the answer
key, E8 the core and helpers, E9 the three adapters.

Names carry the `-v2` suffix (plugin and skill) while v1 `recheck` stays installed; both are
renamed at cutover (ruling 10, 2026-09-13).

Layout planned per the guide (`01-domain/skills-best-practices.md`):

```text
plugins/recheck-v2/
  .claude-plugin/plugin.json          # E8
  README.md
  skills/recheck-v2/
    SKILL.md                          # E8: the portable core
    references/
      pilot-contract.md               # E6: the behavioral contract (this step)
      input.schema.json               # E6: the one validated input structure
      result.schema.json              # E6: the common result
      examples/                       # E6: inputs, results, a checkpoint; validate-examples.py (83 negative, 8 positive, 12 checkpoint checks)
    scripts/                          # E8: deterministic helpers
  agents/openai.yaml                  # E9: Codex adapter
  evals/                              # E7 onward
```
