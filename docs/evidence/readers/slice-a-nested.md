# Slice A evidence — the nested and denied cases from Tony's Codex window (2026-09-06)

Status: authorized run RECORDED (below); refused run pending Tony's paste. The two request files and the mandate are prepared at `/tmp/readers-nest/`; the runs below are recorded verbatim once he pastes the commands into a live Codex window (parent thread on his current model and effort).

Auto-review setting in force on this Mac (`grep -E 'approval_policy|approvals_reviewer' ~/.codex/config.toml`, read 2026-09-06):

```
approval_policy = "on-request"
approvals_reviewer = "auto_review"
```

## Commands for the Codex window

```
~/Developer/tony-skills/plugins/readers/skills/readers/assets/readers /tmp/readers-nest/req-authorized.json
~/Developer/tony-skills/plugins/readers/skills/readers/assets/readers /tmp/readers-nest/req-refused.json; echo exit=$?; ls /tmp/readers-nest/runs/nested/refused
```

Expected: the first prints a result with `"status": "ok"` and a non-empty `raw_text`; the second prints `"status": "unauthorized"`, `exit=1`, and `sidecar.json` alone. If the parent offers an escalation prompt, Tony declines it once for the denied case and the outcome is recorded below; if no prompt appears, the record says so.

## Results

### Authorized nested run (Tony's Codex window, 2026-09-06)

Tony's transcript, verbatim:

```
• I'll check the runner and request file, then run the command if they're ready.
• Explored ... Read req-authorized.json, readers, mandate.txt, readers.py
✔ You approved codex to always run commands that start with ~/Developer/tony-skills/plugins/readers/skills/readers/assets/readers /tmp/re...
• Ran ~/Developer/tony-skills/plugins/readers/skills/readers/assets/readers /tmp/readers-nest/req-authorized.json
  └ { "adapter_version": "slice-a-2026-09-06", ... +41 lines ... "workdir_instruction_files": [] }
• Passed after parent-sandbox escalation: status: ok, exit 0, GPT-6 Astra at low effort.
```

The run directory afterwards (`/tmp/readers-nest/runs/nested/authorized/`): `diagnostics/ dispatch.log output.md raw.md sidecar.json work/`.

`dispatch.log` (two lines: the parent's first attempt hit the startup block, escalated, and the same request file was run again with the same call id):

```
2026-09-06T19:05:38+00:00 dispatch codex exec model=gpt-6-astra effort=low profile=starved
2026-09-06T19:06:15+00:00 dispatch codex exec model=gpt-6-astra effort=low profile=starved
```

`sidecar.json` (the second, successful attempt; the first attempt's sidecar was overwritten because the call id was reused, which the runner now refuses, see Discovered):

```json
{
  "adapter_version": "slice-a-2026-09-06",
  "budget": {
    "estimate_tokens": 397,
    "limit": 272000
  },
  "budget_method": "window-only (row max_output unknown): bytes/3.5 +10% headroom vs window 272000",
  "call_id": "authorized",
  "diagnostics": "/tmp/readers-nest/runs/nested/authorized/diagnostics",
  "dispatch_log": "/tmp/readers-nest/runs/nested/authorized/dispatch.log",
  "duration_s": 9.0,
  "effective_effort": "low",
  "effective_model": "gpt-6-astra",
  "ended_at": "2026-09-06T19:06:24+00:00",
  "envelope": "gpt-astra",
  "exit_code": 0,
  "generation_id": null,
  "isolation": "instruction-only (read)",
  "kind": "portable",
  "mandate_hash": "03f373435b3e319064eb83cb8b838f82ba9a17ae511b09fc2c496fb620b1eba6",
  "memory": null,
  "override_source": "roster default",
  "packet_hash": "d5ed97a088c7066bc88d0c5c42684307e9f9a4bc5f59c9cefb778d7a4a52b315",
  "parity": "web_search: disabled (-c web_search=disabled); sandbox read-only; cwd = fresh empty dir",
  "profile": "starved",
  "protocol_version": 1,
  "raw_file": "/tmp/readers-nest/runs/nested/authorized/raw.md",
  "raw_hash": "e1ebe9959a6c6be504247f2c02be00ccf44269a0e82926634df9dc74887c584d",
  "raw_path": null,
  "raw_text": "It asks for a small, handwritten chalkboard by the bar\u2019s front door, facing the sidewalk, listing today\u2019s drink specials and happy-hour hours. Whoever opens updates it each afternoon, puts it out at opening, and brings it in at close. Success means it is readable from the far curb at 5 pm on weekdays and staff receive fewer than three happy-hour questions per shift.\n\nThe first ambiguity is the end time: **\u201cHappy hour runs until the game starts.\u201d** Which game determines that time, and when does happy hour end on nights with no game?",
  "reason": null,
  "requested_effort": null,
  "requested_model": null,
  "response_raw": null,
  "row": "gpt-astra",
  "run_dir": "/tmp/readers-nest/runs/nested",
  "run_id": "nested",
  "sidecar": "/tmp/readers-nest/runs/nested/authorized/sidecar.json",
  "snapshot": null,
  "started_at": "2026-09-06T19:06:15+00:00",
  "status": "ok",
  "transport": "codex-exec",
  "workdir": "/tmp/readers-nest/runs/nested/authorized/work",
  "workdir_instruction_files": []
}
```

`raw.md` (545 bytes):

```
It asks for a small, handwritten chalkboard by the bar’s front door, facing the sidewalk, listing today’s drink specials and happy-hour hours. Whoever opens updates it each afternoon, puts it out at opening, and brings it in at close. Success means it is readable from the far curb at 5 pm on weekdays and staff receive fewer than three happy-hour questions per shift.

The first ambiguity is the end time: **“Happy hour runs until the game starts.”** Which game determines that time, and when does happy hour end on nights with no game?
```

Parent's approval behaviour observed: Codex asked once to run the command outside its sandbox (the `Operation not permitted` startup block from the scope doc's earlier test); Tony approved it with "always run commands that start with" that prefix, so the prompt will not reappear for these commands in that window.

### Refused run

(paste verbatim)

### Denied case

(the escalation prompt declined, verbatim; or: no escalation prompt appeared; the denied case is not producible under auto-review)
