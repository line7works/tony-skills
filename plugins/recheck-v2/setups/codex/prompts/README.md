# Retained prompts and surfaces

CR means the control-room directory whose absolute path is recorded in ../RESULTS.md. Each CR capture retains command.json, launch.json, rollout.jsonl and final.md. The control room ran these prompts with launch.sh, using the built F1 workspace for probes and the named workspace for each live case. The comparison homes were originally built by hand under the sibling scratch homes/plugin-only and homes/host-only: plugin-only removed the pilot host copies; host-only disabled the pilot plugins. RESULTS.md reuses those measurements, without rerunning them.

install.sh now builds matching separate homes at ~/.local/share/skills-v2-pilot/codex/homes/{plugin-only,host-only}; set RECHECK_CODEX_HOME to the chosen home when invoking launch.sh. The base home has only plugin entries for the pilot. The launcher adds the selected home to its writable roots. Old command.json files distinguish runs before and after that launch change.

Delivery and real-body words prompts explicitly prohibited tool recovery; their records have catalog text only, no body injection. The explicit $name prompts were measured too: host-skill invocation injects a <skill> user message, while the plugin form did not inject a body and the delivery model read the file. Inspect user and developer messages plus tool output records, count UTF-8 bytes yourself, and distinguish file bytes from wrapper bytes. manual-explicit.md is measured on both surfaces; only the host surface recognized it as injected skill content. resource-recovery.md resolved the plugin's own relative reference.

F1-01, F2-01 and F6-04 prompts retain the opaque-built fixture paths. Their old CR sessions stopped on the now-repaired shared-turn collision. This pass did not rerun them. The control room runs the live proofs after this pass. No individual prompt file was changed.

The one extra delivery-cap prompt and capture are retained under pass2/delivery-cap.md and pass2/delivery-cap/. Its cat was blocked by nested sandbox_apply, so the default tool cap remains unmeasured. Nine negative trials use their own prompts and fresh git workspaces; they are not F1 live-proof reruns.
