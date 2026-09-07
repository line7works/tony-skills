# Slice G evidence — jpb converted: the fresh-read request blocks (2026-09-06)

Slice G of `docs/plans/2026-09-06-readers.md`. jpb's six boxes and two judges now summon `/readers`; the conversion is proven pre-merge by greps (AC1, AC2, AC6), the untouched-machinery diff (AC3), one fresh `claude -p` read of the rewritten SKILL.md at its checkout path (AC4) whose eight request blocks are piped one by one to the runner's `validate`, and one live run of the unchanged cost script against Slice B's saved response body (AC5). No model call was sent for this slice: `validate` and `suggest` dispatch nothing, and the cost script is a billing lookup, not a model call. The session model that performed the read reported itself as `claude-fable-5-1`.

`<checkout>` stands for the tony-skills checkout root and `<scratch>` for this session's scratchpad directory (the reads and the runner calls used the absolute paths; scrubbed here per the Slice E convention, Tony's word 2026-09-06). Sizes are bytes (`wc -c`).

## No-spend criteria (run from the repo root at the slice's head)

- AC1: `grep -rilE 'grok|openrouter-box.sh|mcp__codex__codex|mcp__antigravity__ask_gemini|claude-boxes.workflow' plugins/jpb/ | grep -vE 'assets/fixtures/'` → nothing (before the edits: seven files); the marketplace check prints `False True`; the two-deletion test prints `gone`.
- AC2: `grep -ci 'qwen' plugins/jpb/skills/jpb/SKILL.md` → `9`; the `render-page.py` regex check → `True`; the styles JSON check → `True`; `render-page.py` on a scratch run doc holding the fixture's frontmatter and one `## Qwen box — qwen/qwen3.8-max-0902` section exits 0, and the output carries `id="box-qwen" style="--accent:#d96fb0;--tint:#3a2233"` and the Qwen tab; `test-render-page.py` → `render-page fixture check: PASS` (also PASS before the edits). The scratch page was screenshotted through the Playwright MCP at 1440 and 390 px wide: one Brief panel, one Qwen panel in the new rose accent with its `QWEN` badge and tab, Summary; the only console entry was the local server's missing favicon.
- AC3: `git diff --stat main -- <validate-box.py, test-render-page.py, box-mandate.md, box-template.md, openrouter-cost.sh, fixtures/>` → nothing.
- AC6: `grep -c 'readers-protocol: 1' plugins/jpb/skills/jpb/SKILL.md` → `1`.
- Before and after photo: `readers validate` on the nine `assets/examples/*.json` → `valid` nine times both before and after the edits (readers' own files are untouched by this slice); `test-render-page.py` PASS before and after.

## AC5 — the cost path

`plugins/jpb/skills/jpb/assets/openrouter-cost.sh docs/evidence/readers/slice-b-deepseek-response.raw` (the key set in the shell, its existence checked only with the contract's one-liner, never printed) printed, exit 0:

```
gen-1788729077-UZjDzb9vtRxbha4v5YwO 336 338 0.000747489
```

A generation id and a dollar figure (the script's four fields: id, prompt tokens, completion tokens, USD); the script is unchanged and reads the body's top-level `id`.

## The run directory the read was given

Step 5 says the session writes the composed mandate and the brief into the run directory before the fleet, and Step 8 the judge documents, so the read was told a run directory that already existed, prepared by the session exactly as those steps describe, with `assets/fixtures/smoke-brief.md` as the brief (its working name replaced by "the product" to stand for the scrub):

- `<scratch>/jpb-run/box-mandate.md` — `assets/box-mandate.md` with `[TEMPLATE]` replaced by `assets/box-template.md` (2,727 bytes)
- `<scratch>/jpb-run/brief.md` and `judge-brief.md` — the scrubbed brief (487 bytes each)
- `<scratch>/jpb-run/judge-boxes.md` — a one-box stand-in under the vendor-heading contract (67 bytes)

## AC4 — the fleet and the two judge blocks

Command, from the repo root: `claude -p "<prompt>" --output-format text`, where the prompt was:

> Read the file plugins/jpb/skills/jpb/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: a /jpb run whose brief is plugins/jpb/skills/jpb/assets/fixtures/smoke-brief.md; Steps 1 through 3 are done and the scrubbed brief already sits at <scratch>/jpb-run/brief.md and <scratch>/jpb-run/judge-brief.md; the run id is jpb-fresh-read; the run directory is <scratch>/jpb-run; Step 2's suggest has already run (every row available, no drop notes); Step 5's composed mandate already sits at <scratch>/jpb-run/box-mandate.md; the boxes file for the judges already sits at <scratch>/jpb-run/judge-boxes.md; Tony answered "go" at Step 4 with no model switch and no box skipped. Your system prompt names your model id; use it where the skill says to. Print ONLY the JSON request blocks this skill would send to /readers, as one JSON object with three keys: "fleet" (an array of the Step 5 box requests), "judge_k" (the Judge K request object), "judge_g" (the Judge G request object) — absolute paths everywhere, no fence, no prose before or after it, and no other output.

Output, verbatim (stdout; stderr was empty), pretty-printed here for reading:

```json
{
  "fleet": [
    {
      "protocol_version": 1,
      "run_id": "jpb-fresh-read",
      "run_dir": "<scratch>/jpb-run",
      "call_id": "jpb-fresh-read-box-claude-fable",
      "row": "claude-fable",
      "mandate": "<scratch>/jpb-run/box-mandate.md",
      "documents": [
        "<scratch>/jpb-run/brief.md"
      ],
      "profile": "starved",
      "raw_path": "<scratch>/jpb-run/boxes/claude-fable.md",
      "effort": "high"
    },
    {
      "protocol_version": 1,
      "run_id": "jpb-fresh-read",
      "run_dir": "<scratch>/jpb-run",
      "call_id": "jpb-fresh-read-box-claude-opus",
      "row": "claude-opus",
      "mandate": "<scratch>/jpb-run/box-mandate.md",
      "documents": [
        "<scratch>/jpb-run/brief.md"
      ],
      "profile": "starved",
      "raw_path": "<scratch>/jpb-run/boxes/claude-opus.md",
      "effort": "high"
    },
    {
      "protocol_version": 1,
      "run_id": "jpb-fresh-read",
      "run_dir": "<scratch>/jpb-run",
      "call_id": "jpb-fresh-read-box-gpt-astra",
      "row": "gpt-astra",
      "mandate": "<scratch>/jpb-run/box-mandate.md",
      "documents": [
        "<scratch>/jpb-run/brief.md"
      ],
      "profile": "starved",
      "raw_path": "<scratch>/jpb-run/boxes/gpt-astra.md",
      "effort": "high",
      "authorized": true
    },
    {
      "protocol_version": 1,
      "run_id": "jpb-fresh-read",
      "run_dir": "<scratch>/jpb-run",
      "call_id": "jpb-fresh-read-box-gemini",
      "row": "gemini",
      "mandate": "<scratch>/jpb-run/box-mandate.md",
      "documents": [
        "<scratch>/jpb-run/brief.md"
      ],
      "profile": "starved",
      "raw_path": "<scratch>/jpb-run/boxes/gemini.md",
      "authorized": true
    },
    {
      "protocol_version": 1,
      "run_id": "jpb-fresh-read",
      "run_dir": "<scratch>/jpb-run",
      "call_id": "jpb-fresh-read-box-deepseek",
      "row": "deepseek",
      "mandate": "<scratch>/jpb-run/box-mandate.md",
      "documents": [
        "<scratch>/jpb-run/brief.md"
      ],
      "profile": "starved",
      "raw_path": "<scratch>/jpb-run/boxes/deepseek.md",
      "authorized": true
    },
    {
      "protocol_version": 1,
      "run_id": "jpb-fresh-read",
      "run_dir": "<scratch>/jpb-run",
      "call_id": "jpb-fresh-read-box-qwen",
      "row": "qwen",
      "mandate": "<scratch>/jpb-run/box-mandate.md",
      "documents": [
        "<scratch>/jpb-run/brief.md"
      ],
      "profile": "starved",
      "raw_path": "<scratch>/jpb-run/boxes/qwen.md",
      "authorized": true
    }
  ],
  "judge_k": {
    "protocol_version": 1,
    "run_id": "jpb-fresh-read",
    "run_dir": "<scratch>/jpb-run",
    "call_id": "jpb-fresh-read-judge-k",
    "row": "claude-session",
    "session_model": "claude-fable-5-1",
    "mandate": "<checkout>/plugins/jpb/skills/jpb/assets/judge-mandate.md",
    "documents": [
      "<scratch>/jpb-run/judge-brief.md",
      "<scratch>/jpb-run/judge-boxes.md"
    ],
    "profile": "starved",
    "effort": "high",
    "raw_path": "<scratch>/jpb-run/judges/judge-k.md"
  },
  "judge_g": {
    "protocol_version": 1,
    "run_id": "jpb-fresh-read",
    "run_dir": "<scratch>/jpb-run",
    "call_id": "jpb-fresh-read-judge-g",
    "row": "gpt-astra",
    "authorized": true,
    "mandate": "<checkout>/plugins/jpb/skills/jpb/assets/judge-mandate.md",
    "documents": [
      "<scratch>/jpb-run/judge-brief.md",
      "<scratch>/jpb-run/judge-boxes.md"
    ],
    "profile": "starved",
    "effort": "high",
    "raw_path": "<scratch>/jpb-run/judges/judge-g.md"
  }
}
```

What the blocks show: six fleet calls under the one run id `jpb-fresh-read`, call ids `<run id>-box-<row>`, every call `profile: starved` with the mandate by path and the brief as the one document, `raw_path` under `<run dir>/boxes/`; `effort: high` on `claude-fable`, `claude-opus`, and `gpt-astra` only; `authorized: true` on the four outside boxes and on nothing else; the Judge K block on `claude-session` carries `session_model` and no `authorized`; the Judge G block on `gpt-astra` carries `authorized: true` and the same run id; both judges `starved`, effort `high`, the same mandate path and the same two documents.

## Validate, block by block

Each block was piped to `readers validate -` with a placeholder `OPENROUTER_API_KEY` (existence is all the pre-send check needs) under a scratch `READERS_RUN_ROOT` and `READERS_CHECKOUT` pointing at a scratch clone of the checkout, so the tracked `plugins/readers/last-picks.json` never carried test residue (it is unchanged: `{"protocol_version": 1, "picks": {}}`):

```
fleet[0] claude-fable: valid
fleet[1] claude-opus: valid
fleet[2] gpt-astra: valid
fleet[3] gemini: valid
fleet[4] deepseek: valid
fleet[5] qwen: valid
judge_k: valid
judge_g: valid
```

Negative check: the Judge G block with `authorized` removed → `unauthorized`.

Step 2's suggest line, run as the skill states it (`readers suggest claude-fable,claude-opus,gpt-astra,gemini,deepseek,qwen,claude-session --run jpb-fresh-read --run-dir <scratch>/jpb-run`), returned one suggestion per row — `fable`, `opus`, `gpt-6-astra`, `gemini-3.1-pro-high`, `deepseek/deepseek-v4-pro-0813`, `qwen/qwen3.8-max-0902`, and the placeholder `session` for `claude-session` — every row available, no drop notes, memory `ok` at the scratch clone, and wrote the run's snapshot; the Qwen block validated `valid` again against that snapshot.
