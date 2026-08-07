# JPB — Jon's Product Box (vision)

Status: **vision agreed, not built.** Tony gates the build on an explicit "go."
Drafted 2026-08-07 from a phone conversation; this doc is the source of truth
for what /jpb is before any blueprint exists.

## Where it came from

Tony's friend Jon ran product groups (~8 teams of 3). Each team got a physical
box wrapped in paper. Same product brief for everyone. Each team wrote:

- **Front of the box** — product name + logo
- **Back of the box** — the 3 things the product does
- **Side of the box** — 9 smaller details that make it unique

Jon collected the boxes and tallied. Whatever showed up across multiple
independent boxes was the consensus; the disagreements became the debate.
The value is consensus-by-independence: teams that couldn't see each other
converging on the same answer is signal no single team can produce.

## What the skill does

`/jpb <PRD | plan doc path | raw idea text>`

1. Take the input document or idea.
2. **Blind the brief.** Scrub any existing working name, branding, or naming
   language from the input before it reaches the teams, so the front of every
   box is a genuinely independent christening. The scrubbed brief is what all
   five teams receive.
3. Launch **five independent box teams in parallel** — zero shared context;
   each receives only the source input, never each other's boxes:
   - **Builder** — Opus, high effort
   - **Seller** — Opus, high effort
   - **Operator** — Opus, high effort
   - **Generalist** — Fable, high effort
   - **ChatGPT box** — via the Codex MCP connection, their top model
     (Tony's words: "sole" / "5.6" — verify exact model id and whether the
     codex tool exposes model/effort control at build time; fall back to its
     default top model if not)
4. Each team fills out one box:
   - **Front** — product **name**, the **one-sentence pitch** (what it says on
     the tin), and **who it's for** (the single buyer who grabs it off the
     shelf). Replaces Jon's logo — a logo made sense on a shelf, not for
     vetting an idea; the front's real job is "what is this and is it for me"
     in three seconds.
   - **Back** — the **3 things it does**
   - **Side** — the **9 smaller differentiators** — what it does that others
     don't
   - **Bottom (the fine print)** — the **3 assumptions that must be true** for
     this product to work. Not a full pre-mortem (that stays /wargame's job);
     when most boxes list the same fragile assumption, that's the load-bearing
     wall found before framing.
   - **Price tag** — one line: what this team would charge and how (free /
     one-time / subscription). Nice-to-have; Tony is lukewarm — keep it
     because it's one line per box, drop it first if boxes get bloated.
   - Teams work **with web search off** — grounding in the live market would
     converge everyone on what the market already says and pollute the
     independence that makes the exercise work. Vet first, check market after.
5. **Independent judge tally** (Jon collecting the boxes): a fresh judge agent
   that sees only the five boxes — never the conversation that produced the
   idea — clusters the 3s and 9s **by meaning, not wording** ("works offline"
   and "no internet required" are one item), surfaces convergence (items on
   2+, 3+ boxes), names the dissents worth arguing, and notes whether
   name/pitch/buyer themes rhyme. The richest read: same name but different
   buyers across boxes = the debate topic.
6. **Debate card**: the doc ends with the 3 sharpest questions the boxes
   disagree on, written as plain either-or choices — the agenda for the human
   debate.
7. Output: one markdown doc — **all five boxes verbatim** (raw findings always
   preserved so Tony can review each box; the judge's tally never replaces
   them), then the tally, then a recommended front/back/side, then the debate
   card — saved to the current repo's `docs/` folder and summarized in chat.
   **The debate stays human**, like Jon's.

## Practical guards

- Codex connection down or erroring: run the four Claude boxes, say so
  plainly in the output, never fail the whole run.
- `--teams N` override for team count.
- One-line cost warning before launching five high-effort agents.

## Design decisions locked

- Varied lenses (builder/seller/operator) + generalist + cross-vendor ChatGPT
  box, over Jon's identical-mandate teams. Tony chose variety; the cross-model
  box strengthens independence (different model family entirely).
- No git worktrees — box teams write boxes, not code. Isolation comes from
  fresh agents with no shared conversation context (you don't need three job
  sites to get three independent bids — you just don't let the subs see each
  other's numbers).
- Team count adjustable later if wanted; five is the default roster above.
- Position in the loop: **before /blueprint** — JPB vets the idea while it
  doesn't have a name yet. Not a planning tool; a consensus instrument.

## Proposed, not yet committed

- **`/jpb resolve` step** — after the human debate, a follow-up command that
  appends Tony's verdicts to the same doc (chosen name, settled 3, settled 9,
  which dissents were killed), closing it into the input /blueprint wants.
  Tony wants the mechanics expanded before committing to this.

## Open items for build time

- Verify codex MCP tool's model/effort parameters.
- Effort pinning: orchestrate via Workflow (per-agent `effort`) rather than
  bare Agent calls, so "high" is actually enforced for the Claude boxes.
- Skill home: `~/.claude/skills/jpb/` locally; long-term a `jpb` plugin in
  this repo alongside sun/clerk/forge/wargame/signoff.
