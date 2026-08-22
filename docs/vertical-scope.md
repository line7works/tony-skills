# /vertical — scope doc (2026-08-20)

Intent: A whole-build adversarial signoff. After every slice of a build has been
individually signed off and rechecked, /vertical runs ONE big review of the entire
vertical — Claude reviewing at full scope plus outside frontier models (ChatGPT,
Gemini) with a reject-it mandate — merging, deduping, and verifying every finding
into a single verdict doc for Tony. The final inspection before a build is called
done; the capstone of the blueprint → build → signoff → recheck loop.

Decisions:
- The skill exists — decided (Tony ruled it wanted, 2026-08-20 discussion; recorded in the handoff)
- Name is /vertical, final — decided (Tony: "i like vertical", this session)
- Trigger point: runs after all slices of a build are each signed off and rechecked; the review target is the whole vertical against its base — decided (Tony's idea statement in the handoff)
- Outside reviewers: ChatGPT + Gemini only; no DeepSeek for now — decided (this session, models question)
- Every run opens by stopping to ask: local-only review, or local + ChatGPT + Gemini? Tony picks per run — decided (Tony: "is the skill gonna stop and ask me where I want it before it runs it", this session)
- Default answer to the per-run ask is local + both — assumed (proposed in-session as the default, unobjected; one-word reversal at any run)
- The per-run ask always waits for an answer; "default" means the recommended option in the ask, never something silence triggers. Tony answers free-form, and any subset is legal (e.g. "local + ChatGPT only") — assumed (clarification from the cold read; follows Tony's "stop and ask me" ruling)
- Outside models see the FULL code, not just a diff — decided (this session, code-vs-diff question)
- Full code means tracked source: secrets, .env/credential files, and gitignored content are never exposed to outside models — assumed (cold-read catch; no plausible disagreement)
- Stops at the verdict; never fixes anything itself — decided (this session, fix-vs-stop question)
- Skill file lands as ~/.claude/skills/vertical/SKILL.md — assumed (matches every other loop skill's home on disk; small and reversible)
- Scope doc lives in ~/Developer/tony-skills/docs/ — assumed (matches the sibling /digest sitting's convention; no single target repo owns a cross-repo skill)
- Transports reuse /jpb's recorded machinery: GPT via mcp__codex (pinned gpt-5.6-sol), Gemini via mcp__antigravity (gemini-3.1-pro-high), with jpb's parity configs — assumed (both pins and refresh procedures already recorded in ~/.claude/skills/jpb/SKILL.md; reuse was the design premise Tony read back without objection)
- Outside models reach the full code through their own harnesses' repo access (codex works in the checkout; antigravity needs --add-dir), never by pasting source into a prompt — assumed (that is how both tools already operate; mechanics are blueprint altitude)
- Outside findings use /signoff's finding shape: claim · file:line · concrete failure scenario · severity (BLOCKER/MAJOR/MINOR) · confidence — assumed (one template across the loop; mirrors the handoff design Tony read back)
- Claude runs its own /signoff-style review at vertical scope, then merges, dedupes, and adversarially verifies every outside finding before it reaches Tony; nothing unverified lands in the verdict — assumed (matches /signoff's existing verify-before-reporting doctrine; outside models hallucinate file paths)
- Output is one doc, docs/vertical-signoff-<date>.md in the target repo: merged verified verdict at top, every model's raw section verbatim below. THE VERDICT is the merged top section only; the raw sections are a labeled unverified appendix — that is how "nothing unverified lands in the verdict" and "raw sections verbatim" coexist — assumed (mirrors /jpb's output shape; boundary sharpened by the cold read)
- An outside transport that fails mid-run (codex error, agy denial, timeout) is dropped with its reason recorded and the run continues with the survivors; the local Claude review always runs — assumed (jpb's recorded dropped-with-reason pattern)
- Interactive use only, like every other loop skill; no headless/CI mode — assumed (matches the whole loop; cold-read question closed by convention)
- Outside reviewers go in COLD: they receive the build doc (the spec) and the full code, never the per-slice signoff verdicts; Claude holds the prior verdicts and uses them at merge to spot repeats and misses — decided (Round 1 Q1: "they definitely go in cold")
- Invoked with slices not yet signed off/rechecked: report the gap and stop; Tony can collapse the gate in the invocation ("run it anyway"), the skill never does — decided (Round 1 Q2: "report and stop")
- Outside reviewers get the change boundary alongside the full code: the base commit and what the vertical touched, so they know new work from pre-existing code. Cold still holds — no prior verdicts — decided (Round 2 Q1: "give them the boundary")

Out of scope:
- DeepSeek as a reviewer — Tony ruled ChatGPT + Gemini only (cost per run)
- Diff-only disclosure to outside models — Tony chose full code
- Self-fixing after the verdict — Tony ruled it stops at the verdict; fixes are a separate instruction, same as /signoff

Research: ~/Documents/precon-cold-reads/vertical-cold-read-2026-08-21.md (three readers: local Claude, GPT, DeepSeek — DeepSeek added on Tony's word; summary + disposition at top)

Open: (none)

Next: /blueprint when ready.
