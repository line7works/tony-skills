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
3. Launch **three to five independent box teams in parallel** — zero shared
   context; each receives only the scrubbed brief, never each other's boxes.
   **Identical mandates, different frontier models** (adversarial review
   2026-08-07 found the original builder/seller/operator roster fatal:
   three Opus instances in costumes converge on shared weights, not merit —
   independence comes from different model families, like Jon's different
   heads):
   - **GPT box** — via the Codex MCP connection, their top model (verify
     exact model id and control at build time)
   - **Fable box** — high effort
   - **Opus box** — high effort (same vendor as Fable; counts as half a head
     of extra independence, judge weights cross-vendor agreement highest)
   - **Gemini box** — pending access (Gemini CLI install + Google login)
   - **Grok box** — pending access (xAI API key, or OpenRouter key covering
     both)
   Run with whatever subset exists, minimum three; the doc records which
   models filled boxes on each run.
4. Each team fills out one box:
   - **Front** — product **name**, the **one-sentence pitch** (what it says on
     the tin), and **who it's for** (the single buyer who grabs it off the
     shelf). Replaces Jon's logo — a logo made sense on a shelf, not for
     vetting an idea; the front's real job is "what is this and is it for me"
     in three seconds.
   - **Back** — the **3 things it does**
   - **Side** — the **9 things that make it distinctive** — intrinsic
     properties, not competitor comparisons (review: "what others don't do"
     demands the market data web-search-off forbids). At least one item each
     from the build, sell, and run perspectives — the old builder/seller/
     operator lenses live on as required line items inside every box.
   - **Bottom (the fine print)** — the **3 assumptions that must be true** for
     this product to work. Not a full pre-mortem (that stays /wargame's job);
     when most boxes list the same fragile assumption, that's the load-bearing
     wall found before framing.
   - Boxes follow a **strict shared template** (exact headings, exact counts)
     so the judge clusters real content, verbatim inclusion is mechanical,
     and a malformed box is caught by validation before the tally instead of
     silently corrupting it. The GPT box gets the same template; if template
     or no-web parity can't be established for a foreign model, that box is
     dropped for the run and the doc says so.
   - No price tag (review: pure hallucination with web off; Tony was lukewarm
     anyway).
   - Teams work **with web search off** — grounding in the live market would
     converge everyone on what the market already says. The models' training
     priors already carry market knowledge; the point is that no box gets
     fresher ammunition than another. Vet first, check market after.
5. **Independent judge tally** (Jon collecting the boxes): a fresh judge agent
   that sees **the scrubbed brief and the boxes, nothing else** (review: fully
   blind, it can't rank what matters for this idea) clusters the 3s and 9s
   **by meaning, not wording** ("works offline" and "no internet required"
   are one item), and must list every cluster's member items verbatim with
   box attribution so Tony can audit the lumping. Convergence thresholds
   respect model correlation: cross-vendor agreement counts most,
   near-unanimity (4+/5) is the bar for calling something consensus, and
   when the input was a full PRD the back-of-box 3s are reported but
   down-weighted (all boxes read the same brief; paraphrase agreement is
   reading comprehension, not signal). Name convergence is expected and
   weak; name **divergence** is the interesting event.
6. **Debate card**: up to 3 questions the boxes genuinely disagree on, as
   plain either-or choices — and "no material disagreement" is a valid card
   (review: forcing exactly 3 manufactures dichotomies).
7. Output: one markdown doc — **all boxes verbatim** (raw findings always
   preserved so Tony can review each box; the judge's tally never replaces
   them), then the tally, then the debate card — saved to the current repo's
   `docs/` when run inside a repo, else to a fixed ideas home (vault
   project folder or `~/Developer/_ideas/`), with a dated slug so reruns
   never overwrite. **No pre-debate recommendation** (review: it anchors the
   human debate and nobody can write it cleanly — synthesis happens in
   resolve, after Tony has argued). **The debate stays human**, like Jon's.
8. **`/jpb resolve`** — after the human debate, Tony comes back and talks
   through his calls in plain language ("going with name X, buyer is Y, kill
   the white-label idea"). The skill appends a dated **Verdicts** section to
   the same doc recording each call and which box it came from, then marks the
   doc closed. A closed box doc carries a name, pitch, buyer, settled 3 and 9,
   and known assumptions — almost exactly the input /blueprint asks for. The
   pipeline: **jpb → debate → resolve → blueprint → build → signoff.** Without
   resolve, debate outcomes die in the chat; resolve writes the decisions
   where the boxes already are.

## Practical guards

- Any foreign-model box down, erroring, or unable to match the template/no-web
  parity: run the remaining boxes (minimum three), say so plainly in the
  output, never fail the whole run.
- **Scrub procedure is mechanical**: a dedicated low-context agent replaces
  the working name and branding with placeholders ("the product") without
  rewriting the brief, and the scrubbed version is shown to Tony for approval
  before any box launches (review: a rewriting scrubber contaminates all
  boxes identically).
- **Thin-input floor**: a one-line idea can't honestly support 9 distinctive
  properties and 3 assumptions. Below the floor, the skill asks Tony to
  enrich the brief instead of letting boxes pad and the judge cluster the
  padding.
- One-line cost warning before launching the fleet.
- `/jpb resolve` mechanics: fixed filename convention with a status field in
  frontmatter (open/closed); resolve lists open box docs, confirms which one,
  and confirms attribution of each verdict before writing.

## Design decisions locked

- **Identical mandates, different frontier models** (2026-08-07, superseding
  the original builder/seller/operator roster after adversarial review):
  independence comes from different model families, exactly like Jon's
  different heads. The old lenses survive as required line items inside each
  box's side panel.
- No git worktrees — box teams write boxes, not code. Isolation comes from
  fresh agents with no shared conversation context (you don't need three job
  sites to get three independent bids — you just don't let the subs see each
  other's numbers).
- Team count: three to five boxes depending on which model families are
  reachable; roster recorded per run.
- Position in the loop: **before /blueprint** — JPB vets the idea while it
  doesn't have a name yet. Not a planning tool; a consensus instrument.
- Perplexity excluded from the roster: it's a search-wrapped product, and
  live grounding is the thing the exercise turns off.

## Open items for build time

- Verify codex MCP tool's model/effort parameters and whether its web access
  can be disabled for parity.
- Vendor access Tony would need to set up for boxes 4 and 5: Gemini CLI
  (free tier, Google login) and/or an xAI key — or one OpenRouter key
  covering both.
- Verify per-agent effort pinning for the Claude boxes actually enforces
  "high" before adding any orchestration machinery for it.
- Skill home: `~/.claude/skills/jpb/` locally; long-term a `jpb` plugin in
  this repo alongside sun/clerk/forge/wargame/signoff.
