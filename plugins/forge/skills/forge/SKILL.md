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
  a deterministic Python CLI and never calls Fal directly. Supports gen / batch /
  compare / edit / style / finish / resume / init / export / estimate / models,
  transparent-background cut-outs, and per-project brand profiles.
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

## Commands

- Roster and prices: `python3 "$FORGE" models`
- Estimate before spending: `python3 "$FORGE" estimate "<prompt>" --model gpt --size 1024 --quality high`
- Generate one prompt: `python3 "$FORGE" gen "<prompt>" --model nano --size 1024 -n 2 --cap 0.50`
- Generate a shot list: `python3 "$FORGE" batch shots.md --model nano --size 1k --cap 3 --concurrency 4`
- Race models on one prompt: `python3 "$FORGE" compare "<prompt>" --models nano,gpt,flux --cap 0.40`
- Edit an existing image: `python3 "$FORGE" edit <image.png> "<instruction>" --model nano --cap 0.15`
- Generate in a reference style: `python3 "$FORGE" style "<prompt>" --refs <folder> --model nano --cap 0.15`
- Resume an interrupted or partial run: `python3 "$FORGE" resume <run-id> --cap 0.50`
- Re-render keepers at finish quality: `python3 "$FORGE" finish <run-id> <ids...> --model gpt --quality high --size 2048`
- Scaffold a project brand profile: `python3 "$FORGE" init` (writes `.forge/brand.json`)
- Export to size presets (local, free): `python3 "$FORGE" export <image.png> --sizes og,square,icon`
- Add a transparent cut-out to any render: append `--transparent` (runs a bg-removal pass).
- Plan without spending: add `--dry-run`.

A shot list is one shot per line (`id: prompt`), or a `.json`/`.csv` with a `prompt`
plus optional `id`/`model`/`size`/`seed`/`num`/`negative`. `batch` and `compare` also
write a `contact-sheet.html` you can open to eyeball the whole set at once.

Key flags: `--model` (nano | nano-pro | gpt | flux), `--size` (e.g. `1024`, `1024x768`,
`1k`/`2k`/`4k`), `--quality` (gpt only), `-n/--num`, `--seed` (flux), `--cap <usd>`,
`--concurrency <n>`, `--out <dir>`, `--json`.

Output lands in `./generated-assets/<run-id>/raw/` with a `manifest.json` recording
the prompt, model, seed, size, cost, and status for every image. The manifest is what
`resume` reads, so never hand-edit it.

IMPORTANT: a live gpt run can take 30-90s; a multi-shot batch longer. If you run forge
from a shell tool with a timeout, set a generous one (5+ min) or run it in the
background, then poll the manifest. If a run is killed mid-flight, just `resume <run-id>`
— it re-polls in-flight jobs without paying twice and re-submits only what truly failed.

## The foreman loop

1. **Interpret.** Read the request and any references (actually look at the mood-board images).
2. **Estimate.** Run `estimate` (or `gen --dry-run`) and tell Tony the projected cost.
3. **Draft cheap.** Generate on a rough model and size first (nano for flat-vector work). For
   several assets at once, write a shot list and run `batch`. Always pass `--cap`.
4. **Inspect.** Open each output PNG and judge it: misspelled or garbled text, warped
   objects, wrong count, off-brand color (e.g. orange drifting off the project's brand), artifacts.
5. **Fix.** Re-prompt the misses (usually best). For a surgical change to an otherwise-good image
   (strip invented text, swap a color), use `forge edit <image> "<instruction>"`. To hold one style
   across a set, generate with `forge style --refs <folder>`.
6. **Present.** Show Tony the survivors and let him pick. He makes the final call, not you.
7. **Finish.** On Tony's pick, run `forge finish <run-id> <ids...> --model gpt --quality high --size 2048`
   to re-render just the keepers at finish quality (higher res, cleaner, usually drops invented text).
   Finish writes a new run linked to the source; the rough drafts stay untouched.
8. **Deliver.** Add `--transparent` for a cut-out on a transparent background; run
   `forge export <keeper> --sizes og,square,icon` to emit delivery sizes (local, free).

## Brand profiles

If the project has a `.forge/brand.json`, forge auto-loads it for any run inside that project: its
`default_model`/`default_size` become the defaults. You apply the rest by reading the file and folding
it into every prompt you write:

- Run `forge init` once per project to scaffold the profile; it auto-detects the palette from design
  files (DESIGN.md, theme.css). Check what it guessed and correct it before relying on it.
- Append the brand `style` and palette hex(es) to each prompt, e.g. "...flat modern vector, warm
  orange #FF8400 on white, no text". Treat `avoid` as things to keep out of the image by folding
  them into the prompt wording (no model currently takes a separate negative prompt).
- Precedence: an explicit flag Tony gives beats the profile, which beats forge's built-in default.

- Default to cheap models and sizes for drafts; reserve `gpt --quality high` and `nano-pro` for keepers.
- Always pass `--cap`. On `gen` the CLI refuses to start when the estimate exceeds the cap. On
  `batch`/`compare` the cap is a live circuit breaker: forge runs as many shots as fit under it and
  marks the rest `skipped` (never charged); `resume` finishes them once you raise the cap.
- Confirm with Tony before any single run estimated over about $1.

## Picking a model

- `nano` (nano-banana-2): strong, cheap default. Best for flat-vector logos, icons, and mascots —
  clean linework and on-brand color (proven against Commish's brand). It tends to invent text, so
  add "no text" to the prompt when you want none.
- `gpt` (GPT Image 2): quality scales with `--quality`; a clean alternative for character/sticker
  work, ~2x nano's price.
- `flux`: cheapest and supports `--seed`, but it is a photo-diffusion model — it produces soft,
  painterly output and is the WRONG tool for crisp flat-vector brand marks. Use it for textured or
  photoreal rough-ins, not logos.
- `nano-pro`: finish-grade, but still Preview, so it can be flaky.
- Unsure which fits? `forge compare "<prompt>" --models nano,gpt,flux` renders all three side by
  side in one contact sheet.

## Editing and references

- `forge edit <image> "<instruction>"` — natural-language edit of one image, no mask. nano and gpt
  edit through an image array; flux uses Kontext (`fal-ai/flux-kontext/dev`), strong at "change X,
  keep the rest." Default is nano. Local images are sent inline (base64), so just pass a file path.
- `forge style "<prompt>" --refs <folder>` — generate a NEW image conditioned on reference images
  for style/character consistency. Supported on `nano` and `gpt` (they take an image array natively);
  `flux` style needs the paid pro Kontext endpoint and is not wired yet, so use nano or gpt.
- Both obey project cwd and the brand profile, and write the same manifest + contact sheet as `gen`.

## Finishing: transparent backgrounds and export

- `--transparent` on any render (gen/edit/style/finish/batch) adds a background-removal pass
  (birefnet) and writes a `*-transparent.png` cut-out beside the original — for mascots, logos, and
  icons that need to sit on any background. Costs ~$0.04/image extra (unverified estimate) and obeys the cap.
- `forge export <image> --sizes og,square,icon,hero` crops a finished image to named size presets
  with macOS `sips`. Local and free (no API), and it preserves transparency. Presets: og, twitter,
  square, hero, icon, apple-touch, favicon, thumb.
- `resume` does not re-run the transparent pass, and `compare --transparent` is ignored — pass
  `--transparent` on the command that makes the keeper.

## Not for pixel art

For pixel-art game sprites and animations (Project Knight), Tony uses PixelLab. Forge is for
illustration, photoreal, marketing, and concept imagery.
