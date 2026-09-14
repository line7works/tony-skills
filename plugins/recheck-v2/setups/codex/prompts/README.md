# Retained prompts and surfaces

CR is the control-room directory identified in ../RESULTS.md. Captures retain command.json, launch.json, rollout.jsonl and final.md. install.sh builds separate homes/plugin-only and homes/host-only; launch with RECHECK_CODEX_HOME selecting that executor home. E9-25 adds only its child home to writable roots and sets the tool environment to that child through shell_environment_policy.set.

Delivery/real-body words prompts forbid tool recovery. Host explicit $name injects a response_item user skill body with no UserMessage; plugin explicit form requires a file read. manual-explicit.md recognized host injection; plugin file reading still answers PROBE-RAN. resource-recovery.md resolved the installed plugin reference. CR/plugin-only-delivery-cap received the complete real body at default limits (23,332 bytes).

F1-01/F2-01/F6-04 prompt files retain historical fixture paths. Live3 completed after E9-21 but reused fixtures from earlier rounds and recorded dirty source identities. The control room builds fresh fixtures and prompts after pass3, rather than replaying these spent paths. It also runs corrected negative trials and X1-01 from an unsandboxed shell. No live session is launched by the fix-round builder.
