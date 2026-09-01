# Forge — Implementation Spec

> **Status:** Built (M1-M5), full senior review folded in (v0.5)
> **Date:** 2026-06-25
> **Author:** Claude (for Tony)
> **Home:** `tony-skills` plugin (`plugins/forge/`), runs as `/forge`
> **What this is:** the blueprint and permit set for `forge`, a Claude-driven,
> model-agnostic image-generation jig built on Fal.ai. Review and redline before any
> code gets framed.

---

## 1. Goal

A durable, reusable jig that turns a natural request plus a mood board into finished,
on-brand images, with Claude acting as the brain layer and **you choosing which model does
the work**. You say "here's the shot list, mood board is in this folder, go make these," and
forge writes the prompts, generates drafts cheaply, inspects them, fixes problems, lays out a
contact sheet for you to pick from, then renders the keepers at finish quality on whichever
model you want. Every run is logged so it can be repeated or audited later.

This is the general contractor pattern, not a single-shot prompt:
- **The CLI** is the load-bearing structure. It does the mechanical, deterministic work (call
  the API, poll the queue, save files, name them, write the manifest, enforce the cost cap).
  Same inputs produce the same run.
- **The skill** is the foreman. Claude reads the blueprint (your request plus references),
  writes the work orders (prompts), walks the site and inspects with vision, issues
  punch-list fixes, and manages the batch.
- **Fal** is the supply house. One account, one key, every image crew (Nano Banana, GPT Image,
  FLUX) available through a single door, swappable per job.

---

## 2. Design principles

1. **Model choice is yours, per run.** Forge is not wired to one model. Nano Banana, GPT Image
   2, and FLUX are peers behind one Fal key. Pick per job with `--model`, or run `forge compare`
   to see them side by side and choose empirically. Adding a new model is a one-line registry edit.
2. **Deterministic spine.** All side effects (API calls, file I/O, naming, cost math) live in
   the CLI and are logged to a manifest. The LLM only writes prompts and judges images. A run
   is reproducible from its manifest. This is the jig philosophy: build the deterministic tool
   once, run it free forever.
3. **Human holds the final pick.** Vision models, including me, cannot fully judge their own
   image output. I narrow and flag; you choose the keepers. No auto-publish.
4. **Cost governor on by default.** Drafts are cheap, finish is not. Batches default to a cheap
   preset, and `--cap` is a running circuit-breaker: forge tracks actual dollars as each image
   completes and halts the moment the next one would cross your limit. Estimates use conservative
   upper bounds, so the cap holds even where exact pricing is unknown until after the call.
5. **Re-prompt over over-edit.** Image models drift when you nudge one image repeatedly
   (warping, new junk). Forge favors regenerating from a better prompt and uses localized edits
   sparingly and deliberately.

---

## 3. Architecture

```
   You + mood board + shot list
              |
              v
   +-----------------------+   work orders (prompts)
   |  SKILL  =  Foreman     | ------------------------------+
   |  (Claude drives)       |                               v
   |  - writes prompts      |              +----------------------------+
   |  - inspects (vision)   |              |   CLI = the structure       |
   |  - re-prompts / fixes  | <------------|   (deterministic spine)     |
   |  - builds contact sheet|   images +   |   - calls Fal queue          |
   +-----------------------+    manifest   |   - saves + names files      |
              |                            |   - writes run manifest      |
        you pick keepers                   |   - enforces cost cap        |
              |                            +-------------+--------------+
              v                                          | one FAL_KEY
        forge finish                                     v
                                           +----------------------------+
                                           |  Fal = supply house         |
                                           |  swappable crews:           |
                                           |  nano / nano-pro / gpt /flux|
                                           +----------------------------+
```

The skill never talks to Fal directly. It only ever calls the CLI. One throat to choke for
anything that touches money or files, and the whole thing is testable without an LLM in the loop.

---

## 4. Components

### 4.1 The deterministic CLI (`forge`)

| Command | What it does |
| --- | --- |
| `forge gen "<prompt>"` | Generate one or more images from a prompt on the chosen model. |
| `forge batch <shotlist>` | Read a shot-list file (md / json / csv), generate all of it at the cheap preset. |
| `forge compare "<prompt>"` | Run one prompt across several models into a single cost-labeled contact sheet. |
| `forge edit <image> "<instruction>"` | Natural-language edit of an existing image (no mask). |
| `forge finish <run-id> [ids...]` | Re-render selected keepers at the finish preset / higher res. |
| `forge export <image>` | Resize and crop a finished image to named size presets (og, icon, square, hero). Local, no API cost. |
| `forge style --refs <folder>` | Generate conditioned on a reference folder (style + consistency). |
| `forge estimate ...` | Dry-run. Print projected cost for any command, make zero API calls. |
| `forge models` | List the model registry: aliases, Fal ids, current price hints. |
| `forge resume <run-id>` | Re-run only the failed or missing items from a batch that died partway. |
| `forge init` | Scaffold a starter `.forge/brand.json` brand profile in the current project. |

Common flags:

| Flag | Meaning |
| --- | --- |
| `--model <alias>` | Pick the model (`nano`, `nano-pro`, `gpt`, `flux`, ...). |
| `--models a,b,c` | For `compare`: the set to race against each other. |
| `--size <WxH or preset>` | Output size (`1024`, `1080x1080`, `4k`). |
| `--quality <auto\|low\|medium\|high>` | For models that price by quality (GPT Image 2). |
| `--transparent` | Return a cut-out on a transparent background (runs a Fal bg-removal pass after generation). |
| `-n, --num <n>` | Images per prompt. |
| `--concurrency <n>` | How many images run at once against the Fal queue (default 4). |
| `--negative "<text>"` | Reserved negative-prompt flag; no model in the current registry consumes it, so it is silently ignored (kept for a future model that supports it). |
| `--brand <path>` | Use a specific brand profile instead of the auto-detected `.forge/brand.json`. |
| `--seed <n>` | Fix the seed for reproducibility. |
| `--refs <dir>` | Reference images to condition on (used by `style`). |
| `--cap <usd>` | Spend circuit-breaker. Tracks actual cost per image and halts before the next would cross it. |
| `--out <dir>` | Output folder. Defaults to `./generated-assets/`. |
| `--dry-run` | Estimate and plan only, no spend. |
| `--json` | Machine-readable output (how the skill reads results back). |

The CLI is what makes the jig project-aware: run it inside `~/Developer/commish` and the assets
land there. The skill lives globally; the output is local to wherever you invoke it.

### 4.2 The skill (the foreman)

Invoked as `/forge`. Its job is the judgment work the CLI cannot do:

1. **Interpret.** Read your natural request, the shot list, and the mood board images.
2. **Write work orders.** Turn each shot into a precise prompt, folding in style cues read from
   the references.
3. **Rough-in.** Call `forge batch --model nano --json` and pull the draft image paths back.
4. **Inspect (vision QA).** Look at each draft and flag misspelled text, warped anatomy or
   objects, wrong count, off-brand color, artifacts.
5. **Fix.** Re-prompt the failures (preferred) or call `forge edit` for a surgical change.
6. **Contact sheet.** Lay survivors out so you can compare at a glance.
7. **Finish.** On your pick, call `forge finish` to render the keepers on the model and quality
   you chose.

The skill writes nothing to Fal and spends no money directly. Every spend goes through a CLI
command with a visible estimate and cap.

### 4.3 Provider layer (Fal)

- **Auth:** single `FAL_KEY` environment variable. Every Fal client reads it automatically.
- **Calls:** the queue API. The CLI submits a job, polls status, and fetches the result. To stay
  dependency-free (see Packaging), it calls Fal's REST queue endpoints directly rather than
  vendoring an SDK.
- **One door, many models:** every model is the same call shape with a different model id and
  input object. Verified ids are in section 6.
- **Local images go in as data URIs.** For `edit` and `--refs`, the CLI base64-encodes local files
  inline into the model's `image_urls` array (no separate Fal upload step or file lifecycle to
  manage). Files above an 8MB inline ceiling are rejected with a clear "resize it first" message; a
  REST-upload fallback for very large files is deferred to v2.
- **Server-side only:** the CLI runs on your machine, so it uses the key directly. The key must
  never end up in a browser bundle.

### 4.4 Brand profiles (the per-project finish schedule)

A brand profile is a small file saved in a project, `.forge/brand.json`, that records that
project's house style once so you stop re-typing it. When you run forge inside a repo that has
one, the CLI auto-loads it and applies the defaults. It lives in the project, not in the plugin,
so each project carries its own.

Example (`~/Developer/commish/.forge/brand.json`):
```json
{
  "name": "Commish",
  "palette": ["#FF8400"],
  "style": "flat modern vector, soft shadows, friendly, no baked-in text",
  "refs": "./brand/commish",
  "default_model": "gpt",
  "default_size": "1024x1024",
  "avoid": "photorealism, stock-photo look"
}
```

- **Auto-detected.** Run forge anywhere under the repo and it finds `.forge/brand.json`, the way
  `.gitignore` is found. No flag needed.
- **Overridable.** Anything you pass on the command line beats the profile for that run.
- **Scaffolded.** `forge init` writes a starter profile you can edit, so you are not authoring
  JSON from scratch.
- **Precedence:** explicit flag > brand profile > forge built-in default.

---

## 5. Core workflows

**Generate on a chosen model**
```
forge gen "isometric trophy on an orange podium, soft studio light" --model gpt --quality high --size 1024
```

**Compare models on one prompt** (the model-changer feature)
```
forge compare "a friendly league-commissioner mascot, flat vector, brand orange #FF8400" \
  --models nano,gpt,flux -n 1
```
Returns one contact sheet with each model's output labeled by name and cost, so picking the
right crew for this look is data, not a guess.

**Batch from a shot list + mood board** (the headline workflow)
```
forge batch ./shotlists/commish-landing.md --model nano --cap 3
```

A shot list is one shot per row. The simplest form is a Markdown or text list, one brief per line:
```
- standings icon: leaderboard with a trophy on a podium
- schedule icon: a calendar with a whistle
- payments icon: a coin stack with a checkmark
```
For per-shot control, use CSV or JSON rows with optional `id, model, size, seed` columns. The
foreman expands each brief into a full prompt (folding in the brand profile) before the CLI runs it.

**Edit** (use sparingly, watch for drift)
```
forge edit ./generated-assets/<run>/raw/feature-02.png "warm the orange to #FF8400, keep the rest"
```

**Style / consistency from a reference folder**
```
forge style "the four landing-page feature icons as a matching set" --refs ./brand/commish --model nano -n 4
```
Nano Banana 2 accepts up to 14 reference images, which is what makes "generate in this folder's
style" hold together across a set.

**Finish the keepers**
```
forge finish <run-id> feature-01 feature-03 --model gpt --quality high --size 2048
```

**Transparent cut-out** (an icon or mascot meant to sit on a colored section)
```
forge gen "friendly league-commissioner mascot, flat vector" --model gpt --transparent
```

**Export one master to every size you need** (local, no API cost)
```
forge export ./generated-assets/<run>/raw/feature-01.png --sizes og,square,icon,hero
```

### How a real run feels (Commish, the first proving ground)

> **You:** "/forge four feature-section illustrations for the Commish landing page, flat modern
> vector, brand orange #FF8400, mood board in ./brand/commish, 1024 square."
>
> **Me (foreman):** read the brief and the 5 mood images, wrote 4 prompts anchored on #FF8400.
> Since you like choosing, I first ran `forge compare` on shot 1 across `nano`, `gpt`, and
> `flux` for about $0.18 so we could see house style. You liked GPT Image 2's look. I ran
> `forge batch --model gpt --quality medium --cap 3` on all four, pulled back the
> drafts (about $0.40), and inspected them. Icon #3 had a lumpy podium, so I re-rolled it. Here
> is the contact sheet.
>
> **You:** take #1, #2, #4.
>
> **Me:** ran `forge finish` on those three at GPT Image 2 high quality, 2048, about $0.80.
> Manifest logged every generation with prompt, model, seed, and a $1.38 run total. Files are in
> `~/Developer/commish/generated-assets/20260625-141502-landing/final/`. Drop them straight into
> `commish.pen`; text gets composited there, not baked into the image.

---

## 6. Models: registry, switching, and comparison

Forge keeps a small **model registry** (a JSON file in the plugin) mapping friendly aliases to
Fal ids plus price and capability hints. Switching models is `--model <alias>`. Adding a model
is one new entry. `forge models` prints the registry; `forge compare` races a set of them.

Registry shape (illustrative):
```json
{
  "nano":     { "id": "fal-ai/nano-banana-2",   "edit": "fal-ai/nano-banana-2/edit",   "preset": "rough",  "max_refs": 14 },
  "nano-pro": { "id": "fal-ai/nano-banana-pro",  "edit": "fal-ai/nano-banana-pro/edit", "preset": "finish" },
  "gpt":      { "id": "openai/gpt-image-2",       "edit": "openai/gpt-image-2/edit",     "preset": "either", "by_quality": true },
  "flux":     { "id": "fal-ai/flux-1/dev",        "preset": "rough" }
}
```

**Verified catalog (against Fal, 2026-06-25):**

| Alias | Fal id (gen / edit) | Role | Price each | Edit | Multi-ref |
| --- | --- | --- | --- | --- | --- |
| `nano` | `fal-ai/nano-banana-2` (+`/edit`) | cheap workhorse, style refs | $0.06 @512, $0.08 @1K | yes | up to 14 imgs |
| `nano-pro` | `fal-ai/nano-banana-pro` (+`/edit`) | finish-grade, reasoning edits | $0.15, $0.30 @4K | yes | yes |
| `gpt` | `openai/gpt-image-2` (+`/edit`) | rough to premium by quality | $0.01 (low,1K) to $0.41 (high,4K) | yes | yes |
| `flux` | `fal-ai/flux-1/dev` | cheapest rough-in | ~$0.025 | i2i variants | no |

Notes:
- Two finish-grade peers: `nano-pro` and `gpt` at high quality. You are not locked to either.
- Auto-fallback between models (retry a flaky Preview model on a peer) was specced but **deferred to
  v2**: v1 has no `fallback` field and instead surfaces a model error to the foreman, who re-runs on
  another `--model`. `nano-pro` is a Preview alias of `gemini-3-pro-image-preview`.
- GPT Image 2 prices by quality and size, so its `gen` cost spans rough to premium. In v1, `edit`
  and `style` reuse the model's generation price as the estimate (see the `models.json` note);
  token-accurate edit pricing is deferred.
- `nano-pro` is also reachable as `fal-ai/gemini-3-pro-image-preview`.
- Exact input parameter names AND prices per model get locked against each model's `/api` page
  during M1 (a few catalog numbers above are approximate, e.g. nano-banana-2 is ~$0.08 at 1K and
  GPT low lands near $0.005). The registry `models.json` is the single source the estimator reads.

---

## 7. The cost governor

Forge computes an effective per-image estimate from `model + size + quality`, then guards it.

Presets are convenience starting points over the roster, not a cage:

| Preset | Typical pick | ~Each | Use |
| --- | --- | --- | --- |
| `rough` | `flux`, `nano` @1K, or `gpt` low | $0.01 to $0.08 | drafts, exploration, all batches |
| `finish` | `gpt` high or `nano-pro` | $0.15 to $0.41 | keepers only |

Guardrails:
- **Batches default to `rough`.** A 50-image batch is roughly 50 x $0.05 = ~$2.50, not $15.
- **`--cap <usd>` is a circuit-breaker on actuals, not just a start-time guess.** The CLI logs the
  real cost to the manifest after each image and aborts the rest the moment cumulative spend plus
  the next item's upper-bound estimate would exceed the cap. A single call whose upper-bound estimate
  clears a threshold asks for confirmation first. This matters because GPT's edit endpoint is
  token-priced and not knowable exactly before the call.
- **`forge estimate` / `--dry-run`** prints a conservative upper-bound projection with zero API calls.
- **Rough then finish.** You only pay finish-grade on the handful of images that survive
  selection. Rough plumbing before finish carpentry.

---

## 8. Outputs and the run manifest

Folder layout, rooted wherever you run the command:
```
<project>/generated-assets/
  <run-id>/
    manifest.json      # the full record of this run
    raw/               # the images this run produced
    contact-sheet.html # clickable picker (batch / compare / finish / resume)
```
`run-id` format: `YYYYMMDD-HHMMSS-<slug>`, e.g. `20260625-141502-landing`. `forge finish` does not
write a `final/` subfolder; it starts a **new run** (its own `raw/`) linked to the source via
`source_run` in the manifest. `--transparent` writes `*-transparent.png` cut-outs next to the
originals in `raw/`.

The manifest is the deterministic, auditable record:
```json
{
  "schema_version": 1,
  "run_id": "20260625-141502-landing",
  "created_at": "2026-06-25T14:15:02-07:00",
  "command": "batch",
  "cap_usd": 3.00,
  "spent_usd": 0.58,
  "items": [
    {
      "id": "feature-03",
      "status": "completed",
      "prompt": "flat vector league-standings icon, brand orange #FF8400, soft shadow",
      "model": "gpt",
      "fal_id": "openai/gpt-image-2",
      "size": "1024x1024",
      "quality": "medium",
      "seed": 81734,
      "num_images": 1,
      "request_id": "fal-req-9c1...",
      "submitted_at": "2026-06-25T14:15:03-07:00",
      "completed_at": "2026-06-25T14:15:19-07:00",
      "attempts": 2,
      "cost_usd": 0.11,
      "cost_basis": "estimate",
      "outputs": ["raw/feature-03.png"],
      "error": null
    }
  ]
}
```
Per-item `status` is one of `pending | submitted | completed | failed | skipped`. The `status` + `request_id`
pair is what makes `forge resume <run-id>` safe: it re-polls a `submitted`-but-unfetched job instead
of re-paying for it, and only re-submits items that never started. The CLI writes the manifest
**incrementally after each item** and **atomically** (temp file then `os.replace`), so a batch killed
mid-flight never loses the record of paid work.

---

## 9. Vision-QA loop

What the foreman checks on each draft:
- Misspelled or garbled text (the most common image-model failure)
- Warped or extra anatomy and objects
- Wrong count or wrong composition versus the brief
- Off-brand color, lighting, or framing versus the references (e.g. orange drifting off #FF8400)
- General artifacts (smears, melt, doubled elements)

How it fixes:
- **Default: re-prompt.** Tighten the prompt and regenerate. Cleanest, avoids drift.
- **Surgical: `forge edit`.** Only when one localized thing is wrong and the rest is good.
  Flagged in the manifest as an edit so we can see where drift might have crept in.

**The honest caveat:** localized edits on these models are unreliable past a pass or two. The
loop is biased toward "regenerate from a better prompt," and you, not the model, make the final
selection.

---

## 10. Fal setup and onboarding (your one task)

You need a billed Fal key before forge can render. Three steps:

1. **Sign up** at fal.ai (GitHub or Google login).
2. **Add billing.** Dashboard > Billing > add a card. Pay-as-you-go, no subscription or minimum.
   They usually seed a little free credit. Optionally set a monthly spend limit as a second
   backstop to the per-run cap.
3. **Create a key.** Dashboard > API Keys > create. Copy the `FAL_KEY` value once.

**Where to store it:** export it in your shell profile so every project sees it:
```
export FAL_KEY="..."   # in ~/.zshrc
```
The CLI also reads a local gitignored `.env` if you ever want a per-project key.

**Security:** server-side CLI use means the key is used directly, which is fine. Never commit it
and never ship it in a browser bundle. The manifest never stores the key.

---

## 11. Packaging in tony-skills

Forge follows the `sun` pattern (a skill plus bundled scripts), distributed through the
`tony-skills` marketplace.

```
plugins/forge/
├── .claude-plugin/plugin.json   name, description, author, homepage, repository
├── skills/
│   └── forge/SKILL.md           the foreman; trigger-rich frontmatter, /forge body
├── assets/
│   ├── forge.py              the deterministic CLI (single portable script)
│   └── models.json              the model registry
└── IMPLEMENTATION.md            this spec
```

Conventions honored (from the repo CLAUDE.md and README):
- **Dual-mode asset paths.** The skill invokes the CLI via
  `${CLAUDE_PLUGIN_ROOT}/assets/forge.py`, so it resolves both as
  an installed plugin and as a user-level skill. Never hardcode `~/.claude/...`.
- **Dependencies, honestly.** The CLI calls Fal's REST queue directly (`POST
  https://queue.fal.run/<model-id>` with `Authorization: Key $FAL_KEY`, poll, fetch result) using
  only the Python standard library, so generation, edits, and Fal-side work (including
  `--transparent` bg-removal) need nothing installed. Two features need raster work the stdlib
  cannot do: the contact sheet and `forge export` resize/crop. Forge handles these without a Python
  dependency by rendering the contact sheet as an **HTML page** (which doubles as the clickable
  picker) and using macOS's built-in **`sips`** for resize/crop. So on your Mac the CLI stays
  dependency-free; if cross-platform ever matters, swap `sips` for Pillow.
- **Marketplace entry.** Add a `forge` block to `.claude-plugin/marketplace.json`
  (name, source `./plugins/forge`, description, tags like `["image-generation", "automation"]`).
- **Install routes mirror sun.** Plugin route registers `/forge:forge`; the marketplace install
  (`/plugin install forge@tony-skills`) gives the bare `/forge`. You run marketplace installs,
  like your other skills.
- **Branch and PR.** New work goes on a fresh feature branch (`add-forge-plugin`) off `main`, never
  on `main` directly, merged via the PR UI. (This spec is currently an uncommitted file on your
  existing branch; I will cut the proper branch when we start M1.)

---

## 12. Build plan (milestones)

| Milestone | Deliverable | Definition of done |
| --- | --- | --- |
| **M1 Foundation** | Plugin scaffold (plugin.json, SKILL.md, `assets/forge`, `models.json`), `FAL_KEY` wiring, `forge gen`, `forge estimate`, `forge models` | One real image generated end-to-end (try it on a Commish asset), manifest written, cost logged, model selectable via `--model` |
| **M2 Batch + governor + compare** | `forge batch` from a shot list, `--cap`, contact sheet, `forge compare` across models, and batch resilience (concurrency, per-item retry, `forge resume`) | A Commish 4-shot batch runs under a cap and produces a contact sheet; `compare` shows nano vs gpt vs flux side by side; a killed batch resumes only the misses |
| **M3 Foreman QA loop** | Skill wired to the CLI, vision inspection, re-prompt, keeper selection, `forge finish`, and brand-profile auto-load (`forge init`) | A full "request to finished keepers" run with no manual CLI use, with the brand profile applied automatically |
| **M4 Edit + style refs** | `forge edit`, `forge style --refs`, multi-ref consistency | Reference-folder style holds across a 4-image set; a surgical edit works |
| **M5 Finishing** | `--transparent` cut-outs (Fal bg-removal), `forge export` to size presets | A keeper exports to OG, icon, and square sizes; a mascot returns with a clean transparent background |

Each milestone is independently useful. We can stop after any of them and still have a working tool.

**M1 shipped 2026-06-26** (commit `d58584d`): proven live with a first Commish render (~$0.08).
The live run caught and fixed two bugs the design review could not see: a macOS Python empty TLS
trust store (`CERTIFICATE_VERIFY_FAILED`) and Fal's HTTP `202` in-progress status.

**M2 shipped 2026-06-26**: `batch`, `compare`, running cost circuit-breaker, HTML contact sheet,
concurrency + per-item retry, and `resume` — all proven live on Commish. A 4-shot batch under a
tight cap exercised every resilience path at once (one shot skipped by the cap, one isolated 403
failure, two completed); `compare` rendered nano/gpt/flux side by side (nano won for flat-vector
brand work); and a batch killed mid-flight resumed cleanly, re-polling an in-flight gpt job without
re-charging it. A senior code review before close found and fixed three money bugs the live happy
path missed — `resume` double-spend on a transient poll error, an uncapped `resume`, and
`num_images > 1` reserving the price of one image — plus 5xx retry classification, post-submit 404
grace, and non-ASCII id collisions. Live spend to date ~$0.62. The live run also surfaced a Fal
quirk: a burst of concurrent paid submits can trip a spurious "Exhausted balance" 403 on a healthy
account, so forge now treats that as retryable and the foreman defaults to modest concurrency.

**M3 shipped 2026-06-26**: `forge finish` (re-render chosen keepers at finish quality into a new
run linked to the source via `source_run`) and `forge init` (scaffold `.forge/brand.json`,
auto-detecting the brand palette from the project's design files and filtering out neutrals). Brand
auto-load was already in place from M1; the SKILL now wires the full foreman QA loop with
brand-prompt folding. Proven live: a nano-drafted Commish standings icon finished on GPT Image 2 at
high/2048 came back cleaner and text-free (~$0.19), and `init` pulled `#FF8400` out of Commish's
DESIGN.md. A focused senior code review found two issues, both fixed: `finish` would re-render and
charge for a non-completed item selected by id, and `init` raised raw tracebacks on three
filesystem collisions (`.forge` is a file, `brand.json` is a directory, an unwritable target).

**M4 shipped 2026-06-26**: `forge edit <image> "<instruction>"` (natural-language edit, no mask) and
`forge style "<prompt>" --refs <folder>` (reference-conditioned generation). Local images go to Fal
inline as base64 data-URIs — no upload step. Endpoints were verified against fal.ai docs before
coding: nano `.../edit` and gpt `.../edit` take an `image_urls` array (and do multi-ref on the same
endpoint), while flux uses Kontext (`fal-ai/flux-kontext/dev`) with a single `image_url`. Proven
live on Commish: a nano edit stripped invented text from the standings icon (~$0.08), a 2-ref nano
style produced an on-brand whistle icon (~$0.08), and a flux Kontext edit recolored the icon
orange->blue while preserving everything else (~$0.03) — confirming nano accepts inline data-URIs and
the single-image Kontext path. The engine was refactored so every op submits to a per-item endpoint
(`item['fal_id']`), which a senior review confirmed cannot misroute or double-charge; its findings
(fail-loud endpoint resolution, empty-refs guard, an 8MB inline ceiling, reserve-after-build, and a
legacy-manifest self-heal) were folded in. `forge style` on flux needs the paid pro Kontext multi
endpoint and is deferred with a clear message.

**M5 shipped 2026-06-26**: `forge export <image> --sizes og,square,icon,...` (local resize/crop to
named size presets via macOS `sips`, no API, preserves alpha) and a `--transparent` flag on any
render that runs a Fal background-removal pass (`fal-ai/birefnet/v2`, verified against fal.ai docs)
to write an alpha cut-out beside the original. Proven live on Commish: `export` produced exact
og/square/icon/hero crops from a 2048 source with no distortion (free), and `gen --transparent` came
back as a real alpha PNG (`hasAlpha=yes`, ~$0.12 incl. the bg pass). The transparent pass is
cap-aware (counts prior spend, skips before crossing the cap) and never raises. A senior review
confirmed the cap can't be exceeded, the post-pass spend can't be dropped by a later write, and the
crop hits exact preset dimensions for any aspect ratio; its two findings were fixed — `export` now
dies cleanly on a non-image file, and `compare --transparent` warns instead of silently no-op'ing.
The birefnet per-image price ($0.04 in the registry) is a conservative estimate pending a dashboard
check. This completes the M1-M5 roadmap.

**Full senior review folded in 2026-06-26** (post-M5, pre-PR): an independent five-dimension review
of the whole plugin (money/concurrency, Fal API, error handling, security, code quality). Security
came back clean (key never leaks, no shell injection, TLS verification stays on, output paths are
slug-guarded). Fixes applied across P1-P5:
- **No double-pay (P1).** Retries and `resume` now re-poll an existing job instead of re-submitting,
  so a transient blip *after* a successful submit can never pay for a second generation; the submit
  is the only step gated by "no live request yet" (`_run_job`). `_resume_terminal` no longer treats a
  CDN download blip as a dead job (which had re-charged), and an empty/"no images" result is now
  terminal so `resume` can't defer it forever.
- **Cap honesty (P2).** A failed item releases its reservation, so `--cap` gates *spend*, not
  *attempts*; the transparent pass and `persist` share one `manifest_spent` formula (gen +
  background-removal), so transparent spend can't be silently dropped; a re-polled in-flight job is
  committed to the breaker.
- **Robustness (P2/P3).** `poll_job` detects Fal's error-on-`COMPLETED` and uses a wall-clock
  timeout; `download` writes atomically and verifies `Content-Length`; `resume`'s re-poll catches all
  exceptions (not just `RuntimeError`); `--num/--cap/--concurrency` are validated at parse time (the
  `resume --concurrency` traceback is gone).
- **Maintainability (P4/P5).** The submit/poll/retry and cost-ledger logic was factored into shared
  helpers (`_run_job`, `_with_retry`, `_Ledger`, `manifest_spent`); the job tuple became a namedtuple;
  the dead `fallback` field, the inert `image_urls` param, and stale `--preset` doc references were
  removed.

Verified by an offline money-safety test harness (no-double-pay, cap enforcement, release-on-failure,
classifier coverage) plus the no-key CLI paths. The only deliberate non-fix: a `fetch_result` 202
race window and birefnet's placeholder price, both low-risk and noted.

---

## 13. Decisions

Almost everything is settled. Nothing here needs action from you except an optional override on
the language. The only real task on your side is the Fal key in section 10, which gates a live
render (not the build).

| Decision | Status |
| --- | --- |
| **Language** | DECIDED: **Python 3**, matching the `sun` plugin's bundled scripts. The CLI is stdlib-only for all Fal work; the contact sheet is HTML and `export` uses macOS `sips`, so no Python packages are required on your Mac. |
| Name | LOCKED: `forge`. |
| Home | LOCKED: `tony-skills` plugin, user-level install like your others. |
| Models | LOCKED: multi-model with easy switching. Roster: `nano`, `nano-pro`, `gpt`, `flux`, easily extended. |
| First target | LOCKED: Commish (your most active app work right now). |
| Key storage | DEFAULT: `FAL_KEY` in shell profile, `.env` override available. No action needed. |

---

## 14. Out of scope (v2 and later)

- **Video.** Fal also hosts video models (Veo, Kling, etc.) behind the same key. The same jig
  shape could drive them later. Not in v1.
- **Dedicated upscaler chain.** v1 "finish" just re-renders at higher resolution. A real
  upscale-the-winner pass is a v2 add.
- **A clickable contact-sheet picker.** v1 contact sheet is a generated image grid plus the
  manifest. A real picker UI is later.
- **Per-project automation hooks** (auto OG images on deploy, scheduled social batches). Possible
  once the jig is proven on Commish.

---

## 15. Senior review dispositions (v0.4)

An independent senior-engineer review signed off **with conditions** on 2026-06-25. Resolutions:

**Blocking (resolved in this spec):**
- **Dependency claim was false for raster work.** Contact sheet and `export` cannot run on Python
  stdlib. Resolved: HTML contact sheet (doubles as the v2 picker) + macOS `sips` for resize/crop;
  CLI stays dependency-free on macOS (sections 11, 13).
- **`--cap` was not airtight** given token-priced GPT edits. Resolved: cap is a running
  circuit-breaker on actual spend, with conservative upper-bound gating and a confirm threshold
  (sections 2, 7).
- **Local-image upload for edit/refs was unspecified.** Resolved: base64 data-URI inline into the
  model's `image_urls` array, REST-upload fallback for large files (section 4.3).

**Should-fix (folded in):**
- Manifest extended with `schema_version`, per-item `status`, `request_id`, timestamps, `attempts`,
  and `error`, written incrementally and atomically so `resume` never double-spends (section 8).
  These fields land in M1's manifest writer so M2 does not retrofit the schema.
- Fallback behavior pinned: one retry, fallback default quality, same cap, surfaced not just logged
  (section 6).
- Retry/backoff on 429/5xx, per-item timeout, and a manifest-write lock under `--concurrency` are
  part of M2's batch resilience (section 12).
- Model prices/ids reconciled against each `/api` page in M1; `models.json` is the estimator's
  single source (section 6).

**Hardening (in the M1 build):**
- `python3` preflight in the skill: a missing or old interpreter fails loudly, unlike sun's
  best-effort cosmetic scripts.
- `forge` uses its own `${CLAUDE_PLUGIN_ROOT}` asset path, not sun's shared one.
- On first run in a project, forge ensures `generated-assets/` and `.env` are gitignored in the host
  repo, since assets land in arbitrary project dirs.

**Confirmed sound:** the foreman/CLI split, the Fal queue-over-REST approach (submit/poll/fetch
verified), `FAL_KEY` handling, the dual-mode `${CLAUDE_PLUGIN_ROOT}` invocation, and M1 as the right
first slice.
