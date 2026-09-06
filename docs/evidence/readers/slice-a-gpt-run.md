# Slice A evidence — the GPT lane, live (2026-09-06)

Row `gpt-astra` (`gpt-6-astra`, effort `low`), transport `codex exec` 0.153.4, profile `starved`, fixture `plugins/readers/skills/readers/assets/fixtures/smoke-doc.md`. Scratch paths are shown as `<scratch>`. A first AC2 run was made before R9's labels were recorded (its sidecar said `unmeasured`); the run below is the recorded AC2, made after the roster carried the measured label, so its `raw_path` copy took the `-2` collision suffix (Slice A R7's rule, exercised).

## AC2 — request

```json
{"protocol_version":1,"run_id":"ac2","call_id":"live1","row":"gpt-astra","mandate":"<scratch>/mandate.txt","documents":["~/Developer/tony-skills/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md"],"profile":"starved","authorized":true,"raw_path":"<scratch>/ac2-raw.md"}
```

## AC2 — command the runner built (diagnostics/command.txt)

```
codex exec -m gpt-6-astra -c model_reasoning_effort=low -c web_search=disabled -s read-only -C <scratch>/runs/ac2/live1/work --skip-git-repo-check --json -o <scratch>/runs/ac2/live1/output.md -
```

## AC2 — result (stdout)

```json
{
  "adapter_version": "slice-a-2026-09-06",
  "budget": {
    "estimate_tokens": 423,
    "limit": 272000
  },
  "budget_method": "window-only (row max_output unknown): bytes/3.5 +10% headroom vs window 272000",
  "call_id": "live1",
  "diagnostics": "<scratch>/runs/ac2/live1/diagnostics",
  "dispatch_log": "<scratch>/runs/ac2/live1/dispatch.log",
  "duration_s": 23.0,
  "effective_effort": "low",
  "effective_model": "gpt-6-astra",
  "ended_at": "2026-09-06T19:00:01+00:00",
  "envelope": "gpt-astra",
  "exit_code": 0,
  "generation_id": null,
  "isolation": "instruction-only (read)",
  "kind": "portable",
  "mandate_hash": "6d4bb9cdcf2a15fbe1bebdfb071de34cd20f402d862f6095fa4686e1ff2b0134",
  "memory": null,
  "override_source": "roster default",
  "packet_hash": "4527e8ff10456458feb33c3264a69152d6a1854e8bbe5e303fa58f058f132649",
  "parity": "web_search: disabled (-c web_search=disabled); sandbox read-only; cwd = fresh empty dir",
  "profile": "starved",
  "protocol_version": 1,
  "raw_file": "<scratch>/runs/ac2/live1/raw.md",
  "raw_hash": "0da1a096929d5ecb6bde15f8344804da85ac3676476aefa118b4746c7c239d7d",
  "raw_path": "<scratch>/ac2-raw-2.md",
  "raw_text": "**1. What it asks for**\n\nA small, handwritten chalkboard by the bar\u2019s front door, facing the sidewalk, showing today\u2019s drink specials and happy-hour hours. Whoever opens writes it each afternoon; staff put it out at opening and bring it in at close. It should be readable from the far curb at 5 pm on a weekday and reduce questions to fewer than three per shift. Printed or lit signs and online posting are excluded.\n\n**2. Ambiguities or gaps**\n\n- **\u201cuntil the game starts\u201d**: Which game determines the end time? What happens with no game?\n- **\u201cdrink specials and the hours\u201d**: The actual specials, their prices or terms, happy-hour start time, and source for today\u2019s information are missing.\n- **\u201ceach afternoon\u201d / \u201cat opening\u201d**: Opening and closing times are unstated. If opening precedes afternoon writing, when must the sign be ready?\n- **\u201csmall\u201d / \u201cby the front door\u201d**: No dimensions or precise placement are specified.\n- **\u201creadable from the far curb\u201d**: Which curb or viewing point, under what conditions, and who judges readability?\n- **\u201cOn a weekday at 5 pm\u201d**: Which weekday, or every weekday? Must opening occur before 5?\n- **\u201cfewer than three \u2026 per shift\u201d**: Which shifts, over what evaluation period, and how are questions counted?",
  "reason": null,
  "requested_effort": null,
  "requested_model": null,
  "response_raw": null,
  "row": "gpt-astra",
  "run_dir": "<scratch>/runs/ac2",
  "run_id": "ac2",
  "sidecar": "<scratch>/runs/ac2/live1/sidecar.json",
  "snapshot": null,
  "started_at": "2026-09-06T18:59:38+00:00",
  "status": "ok",
  "transport": "codex-exec",
  "workdir": "<scratch>/runs/ac2/live1/work",
  "workdir_instruction_files": []
}
```

## AC2 — sidecar.json

```json
{
  "adapter_version": "slice-a-2026-09-06",
  "budget": {
    "estimate_tokens": 423,
    "limit": 272000
  },
  "budget_method": "window-only (row max_output unknown): bytes/3.5 +10% headroom vs window 272000",
  "call_id": "live1",
  "diagnostics": "<scratch>/runs/ac2/live1/diagnostics",
  "dispatch_log": "<scratch>/runs/ac2/live1/dispatch.log",
  "duration_s": 23.0,
  "effective_effort": "low",
  "effective_model": "gpt-6-astra",
  "ended_at": "2026-09-06T19:00:01+00:00",
  "envelope": "gpt-astra",
  "exit_code": 0,
  "generation_id": null,
  "isolation": "instruction-only (read)",
  "kind": "portable",
  "mandate_hash": "6d4bb9cdcf2a15fbe1bebdfb071de34cd20f402d862f6095fa4686e1ff2b0134",
  "memory": null,
  "override_source": "roster default",
  "packet_hash": "4527e8ff10456458feb33c3264a69152d6a1854e8bbe5e303fa58f058f132649",
  "parity": "web_search: disabled (-c web_search=disabled); sandbox read-only; cwd = fresh empty dir",
  "profile": "starved",
  "protocol_version": 1,
  "raw_file": "<scratch>/runs/ac2/live1/raw.md",
  "raw_hash": "0da1a096929d5ecb6bde15f8344804da85ac3676476aefa118b4746c7c239d7d",
  "raw_path": "<scratch>/ac2-raw-2.md",
  "raw_text": "**1. What it asks for**\n\nA small, handwritten chalkboard by the bar\u2019s front door, facing the sidewalk, showing today\u2019s drink specials and happy-hour hours. Whoever opens writes it each afternoon; staff put it out at opening and bring it in at close. It should be readable from the far curb at 5 pm on a weekday and reduce questions to fewer than three per shift. Printed or lit signs and online posting are excluded.\n\n**2. Ambiguities or gaps**\n\n- **\u201cuntil the game starts\u201d**: Which game determines the end time? What happens with no game?\n- **\u201cdrink specials and the hours\u201d**: The actual specials, their prices or terms, happy-hour start time, and source for today\u2019s information are missing.\n- **\u201ceach afternoon\u201d / \u201cat opening\u201d**: Opening and closing times are unstated. If opening precedes afternoon writing, when must the sign be ready?\n- **\u201csmall\u201d / \u201cby the front door\u201d**: No dimensions or precise placement are specified.\n- **\u201creadable from the far curb\u201d**: Which curb or viewing point, under what conditions, and who judges readability?\n- **\u201cOn a weekday at 5 pm\u201d**: Which weekday, or every weekday? Must opening occur before 5?\n- **\u201cfewer than three \u2026 per shift\u201d**: Which shifts, over what evaluation period, and how are questions counted?",
  "reason": null,
  "requested_effort": null,
  "requested_model": null,
  "response_raw": null,
  "row": "gpt-astra",
  "run_dir": "<scratch>/runs/ac2",
  "run_id": "ac2",
  "sidecar": "<scratch>/runs/ac2/live1/sidecar.json",
  "snapshot": null,
  "started_at": "2026-09-06T18:59:38+00:00",
  "status": "ok",
  "transport": "codex-exec",
  "workdir": "<scratch>/runs/ac2/live1/work",
  "workdir_instruction_files": []
}
```

## AC2 — checks

- `cmp <run dir>/live1/raw.md <run dir>/live1/output.md` printed nothing; `cmp <raw_path copy> <run dir>/live1/output.md` printed nothing.
- every-field check (`python3 -c ... print([k for k in keys if k not in s])`) printed `[]`.
- `grep -rc 'Authorization' <diagnostics dir>` printed `0` for every file (stderr.txt, command.txt, events.jsonl).
- `workdir_instruction_files` was `[]`: the child's fresh `work/` directory carried no `AGENTS.md` or `CLAUDE.md`. Codex also reads `~/.codex/AGENTS.md` when present; that is outside the working directory and not measured here.

## AC3 — the seven refusals

Each request carried `authorized: true` except the first. Each exited 1 and `ls <run dir>/ac3/<call id>` printed `sidecar.json` alone.

| call | request difference | status | reason |
|---|---|---|---|
| r1 | no `authorized` on gpt-astra | `unauthorized` | outside row gpt-astra without the authorized flag (Tony's word in this run) |
| r2 | claude-session, floor opus, session_model claude-haiku-4-5-20251001 | `floor-refused` | session model claude-haiku-4-5-20251001 is below floor opus |
| r3 | gpt-astra, floor opus, model some-new-id | `unknown-model` | typed id some-new-id is not classified against floor opus |
| r4 | gpt-astra, profile repo-with-tools | `profile-unsupported` | row gpt-astra does not support profile repo-with-tools (supports ['starved', 'packet-only', 'repo']) |
| r5 | protocol_version 0 | `version-mismatch` | request protocol_version 0, runner 1 |
| r6 | row no-such-row | `invalid-request` | unknown row id: no-such-row |
| r7 | document of 1,088,000 bytes (window x 4) | `oversize` | estimated 341957 tokens exceeds limit 272000 (window-only (row max_output unknown): bytes/3.5 +10% headroom vs window 272000) · budget {'estimate_tokens': 341957, 'limit': 272000} |

## AC4 — validate

`readers validate` on AC2's request printed `valid` (exit 0); on the AC3 oversize request it printed `oversize`; on the AC12 request it printed `valid` (validate does not apply the host-row rule).

## AC7 — concurrency

Two authorized fixture reads launched in the background with `run_id` `ac7` and call ids `ac7a`, `ac7b`; after `wait`, `find <run dir>/ac7 -name sidecar.json | wc -l` printed `2`, the two `raw.md` files sat in `ac7/ac7a/` and `ac7/ac7b/`, and the intervals overlapped:

- ac7a: `ok` · 2026-09-06T18:58:50+00:00 → 2026-09-06T18:59:10+00:00
- ac7b: `ok` · 2026-09-06T18:58:50+00:00 → 2026-09-06T18:59:09+00:00

## AC12 — a host row from the shell

Request naming row `gemini` (authorized, fixture, starved) through the entry: exit 1, status `lane-unavailable`, reason: host lane gemini (antigravity-mcp) cannot run from the shell entry; summon /readers from the skill body. `ls <run dir>/ac12/g1` printed `sidecar.json` alone. `readers validate` on the same request printed `valid`.
