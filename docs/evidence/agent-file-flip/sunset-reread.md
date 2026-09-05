# agent-file-flip — sunset re-read (2026-09-04)

Slice D, R3. Re-read of `plugins/sun/skills/sunset/SKILL.md` on branch `feat/agent-file-flip-d` (file unchanged since main 567866c; not in any slice's footprint).

**Finding:** the file reads or writes no repo instruction file. Its one `AGENTS.md` mention is the vault guard at line 83, which tests that `~/ObsidianVault/AGENTS.md` exists to tell the canonical vault from a stub. It never opens a repo's `AGENTS.md`, `CLAUDE.md`, or `REVIEW.md`; the repo it archives moves whole into `~/Developer/_archive`, so any loop artifact under `docs/` travels with it untouched. Nothing in the file needs to change for the agent-file flip.

Command and output, run 2026-09-04:

```
$ grep -n "AGENTS.md\|CLAUDE.md" plugins/sun/skills/sunset/SKILL.md
83:elif [ ! -f "$V/AGENTS.md" ];           then echo "STOP: $V has no AGENTS.md — stub, not canonical"
```
