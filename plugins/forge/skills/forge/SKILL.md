---
name: forge
description: >-
  Generate AI images on Fal.ai with Claude as the brain layer: write the prompts,
  generate drafts, inspect them with vision, fix problems, and render finished
  on-brand images. Use when Tony wants to create, generate, or make images,
  illustrations, icons, a mascot, key art, marketing graphics, hero images, OG or
  social cards, backgrounds, or concept art; asks to "make an image of X",
  "generate N images of Y", or "an image for <project>"; or wants to run a shot
  list against a mood board. Model-agnostic (nano-banana, GPT Image 2, FLUX,
  swappable per job with --model), with a per-run cost cap and an auditable run
  manifest. NOT for pixel-art game sprites (Tony uses PixelLab for those). Drives
  a deterministic Python CLI and never calls Fal directly. Today (M1) it supports
  gen / estimate / models; batch, compare, edit, finish, export, and brand
  profiles arrive in later milestones.
---

# Forge: Claude-driven image generation

You are the foreman. The blueprint is Tony's request plus any mood board or
references; the crew is a Fal image model; the structure that does the real work
is the `forge` Python CLI. You write the work orders (prompts), run the CLI,
inspect what comes back with your own vision, fix problems, and hand Tony a clean
set to choose from. You never call Fal directly, and you never spend without
showing the estimate first.

## The CLI

It lives next to this skill. Always invoke it by this path so it resolves both as
an installed plugin and as a user-level skill:

```bash
FORGE="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/forge}/assets/forge.py"
python3 "$FORGE" <command> [args]
```

Pass `--json` on any command to read structured results back.

## Preflight (once, before the first render)

1. `python3 --version` must be 3.8+. If `python3` is missing, stop and tell Tony
   to install it; the CLI is load-bearing and cannot run without it.
2. For live renders, `FAL_KEY` must be set (check `echo "${FAL_KEY:+set}"`). If it
   is empty, point Tony to IMPLEMENTATION.md section 10 (sign up at fal.ai, enable
   billing, `export FAL_KEY=...`). `estimate`, `models`, and `gen --dry-run` all
   work without it.
3. Run inside the target project so assets land there, e.g. `cd ~/Developer/commish`
   before generating Commish art.

## Commands available now (M1)

- Roster and prices: `python3 "$FORGE" models`
- Estimate before spending: `python3 "$FORGE" estimate "<prompt>" --model gpt --size 1024 --quality high`
- Generate: `python3 "$FORGE" gen "<prompt>" --model nano --size 1024 -n 2 --cap 0.50`
- Plan without spending: add `--dry-run`.

Key flags: `--model` (nano | nano-pro | gpt | flux), `--size` (e.g. `1024`, `1024x768`,
`1k`/`2k`/`4k`), `--quality` (gpt only), `-n/--num`, `--seed` (flux), `--cap <usd>`,
`--out <dir>`, `--json`.

Output lands in `./generated-assets/<run-id>/raw/` with a `manifest.json` recording
the prompt, model, seed, size, cost, and status for every image.

## The foreman loop

1. **Interpret.** Read the request and any references (actually look at the mood-board images).
2. **Estimate.** Run `estimate` (or `gen --dry-run`) and tell Tony the projected cost.
3. **Draft cheap.** Generate on a rough model and size first (nano or flux). Always pass `--cap`.
4. **Inspect.** Open each output PNG and judge it: misspelled or garbled text, warped
   objects, wrong count, off-brand color (e.g. orange drifting off the project's brand), artifacts.
5. **Fix.** Re-prompt the misses (preferred over editing). Regenerate.
6. **Present.** Show Tony the survivors and let him pick. He makes the final call, not you.
7. **Finish.** (Later milestone) re-render the keepers at finish quality.

## Cost discipline

- Default to cheap models and sizes for drafts; reserve `gpt --quality high` and `nano-pro` for keepers.
- Always pass `--cap` on multi-image runs. The CLI refuses to start a run whose estimate exceeds the cap.
- Confirm with Tony before any single run estimated over about $1.

## Picking a model

- `nano` (nano-banana-2): strong, cheap default; good for illustration and style refs.
- `gpt` (GPT Image 2): quality scales with `--quality`; Tony likes it for Commish.
- `flux`: cheapest rough-in; supports `--seed` for reproducibility.
- `nano-pro`: finish-grade, but still Preview, so it can be flaky.
- Unsure which fits? `forge compare` (a later milestone) races several on one prompt.

## Not yet implemented

`batch`, `compare`, `edit`, `finish`, `export`, `style`, `resume`, and `init` are on the
roadmap (M2-M5). Do not call them yet. For now, drive `gen` per shot and assemble sets by hand.

## Not for pixel art

For pixel-art game sprites and animations (Project Knight), Tony uses PixelLab. Forge is for
illustration, photoreal, marketing, and concept imagery.
