# Slice A evidence — the nested and denied cases from Tony's Codex window (2026-09-06)

Status: PENDING Tony's paste. The two request files and the mandate are prepared at `/tmp/readers-nest/`; the runs below are recorded verbatim once he pastes the commands into a live Codex window (parent thread on his current model and effort).

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

(not yet run)

### Authorized nested run

(paste verbatim)

### Refused run

(paste verbatim)

### Denied case

(the escalation prompt declined, verbatim; or: no escalation prompt appeared; the denied case is not producible under auto-review)
