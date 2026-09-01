# tony-skills

A Claude Code plugin marketplace: the skills Tony Coon builds and runs on his
own machines, published so anyone can install them. Nineteen plugins covering
twenty skills — a full build loop (blueprint → build → signoff → recheck, with
/ship to run a whole lap), project lifecycle bootstrapping, image generation,
adversarial reviews, and a handful of workshop utilities — plus a `tools/`
shelf of non-plugin tools and specs.

## Install

Add the marketplace, then install any plugin from it:

```
/plugin marketplace add line7works/tony-skills
/plugin install huh@tony-skills
```

Swap `huh` for any plugin below. Update later with
`/plugin update <name>@tony-skills`.

**Fair warning:** these are personal, working skills, shared as-is. Several are
wired to Tony's own setup — absolute paths under `~/Developer`, machine names,
a two-Mac relay protocol, live production endpoints for his sites. The
self-contained ones (`huh`, `wargame`, `signoff`, `recheck`, `blueprint`,
`build`, `ship`, `digest`) travel well. Others carry hard-wired paths into
Tony's clone of this repo — `inspect` reads its code book from
`~/Developer/tony-skills/...` at run time, `fb` routes loop notes to a file
there, `precon` points at jpb by the same path — so they, like the
machine-wired rest, are best read as reference implementations you adapt
rather than run unmodified.

## The plugins

**The build loop** — a paper-trail-driven construction loop for shipping
features in verified slices. Each station is a skill, composed by name:

- `precon` — harvest a free-flowing idea discussion into a fixed-format scope doc
- `jpb` — Jon's Product Box: 3–6 independent frontier-model "box teams" vet an idea before it has a name
- `blueprint` — draft a build doc in dependency-ordered, verifiable slices
- `inspect` — adversarial review of a build doc *before* anything is built
- `build` — execute one slice inside strict boundaries; honest stops over fake completeness
- `signoff` — independent adversarial review of the built slice by reviewers who didn't write it
- `recheck` — closed-checklist re-inspection that verifies named fixes and flips the card
- `ship` — one command that runs a slice through the whole loop with a hard lap limit
- `vertical` — the whole-build capstone review once every slice is signed off
- `handoff` — end-of-slice thread prep: record rulings, write the handoff block, hand over the kickoff line
- `fb` / `digest` — capture feedback notes verbatim / compile them into a current-state notes board
- `huh` — re-explain the pending question in plain language, ending with a recommendation

**Project lifecycle:**

- `sun` — `/sunrise` bootstraps a new project across every layer (repo, GitHub,
  Vercel, database, Notion, Obsidian, memory) and proves it live; `/sunset`
  archives one reversibly. One plugin, shared assets.
- `shutdown` — settle up before a terminal restart or account switch: git
  report, self-contained handoff file, memory pointer.

**Making things:**

- `forge` — Claude-driven image generation on Fal.ai: the skill writes prompts,
  runs vision QA, and renders on-brand images through a bundled
  dependency-free Python CLI. Model-agnostic, cost-capped, manifest-audited.
- `wargame` — adversarial pre-mortem of any target; ranked, verified failure
  modes with an anti-theater rule (high-ranked failures must convert to real
  checks). Opus-class model floor.
- `print-tune` — collaborative per-setting print tuning for the Bambu H2C,
  driven by a sourced setting playbook.
- `arcade` — publish, update, reorder, and take down pages on the Line 7
  Arcade (Tony's live site) via the bundled `arcade-publish` CLI.

## Tony Tools (`tools/`)

Things a human copies, runs, or reads directly — not installed through Claude
Code:

- **`gmail-mcp/`** — a multi-account Gmail MCP server (real, installable).
  Deliberate ceilings: `gmail.modify` scope only (no permanent delete),
  required account aliases, confirm-gated sends. Credentials live outside the
  repo, always.
- **`antigravity-mcp/`** — an MCP server wrapping Google Antigravity's `agy`
  CLI so Claude Code can consult Gemini (real, installable), with documented
  workarounds for verified `agy` behaviors.
- **`mcp-obsidian-worker/`** — implementation spec for a Cloudflare Worker
  exposing an Obsidian vault over MCP (spec only; the source lives elsewhere).
- **`arcade-publish/`** — the findings ledger from the arcade CLI's build; the
  CLI itself ships inside `plugins/arcade/assets/`.

## Layout

```
.claude-plugin/marketplace.json   the catalog — 19 entries
plugins/<name>/                   one plugin per skill (sun bundles sunrise+sunset)
  .claude-plugin/plugin.json
  skills/<skill>/SKILL.md         (+ assets/, nested or at plugin root)
docs/                             build plans, reviews, and the loop's paper trail
tools/                            the non-plugin shelf
```

The `docs/` folder is the workshop's real paper trail — build plans, scope
docs, adversarial reviews, evidence files. It ships in the repo on purpose:
the loop skills above produced it, so it doubles as their worked example.

## License

MIT — see [LICENSE](LICENSE).
