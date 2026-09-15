"""The fake harness: a scripted executor that runs the real core with no model.

The three stub launchers under this directory (`claude-code-launch.sh`, `codex-launch.sh`,
`opencode-launch.sh`) call this module with the arguments their real counterpart takes. It
does exactly what a real session does, minus the model:

1. reads the run directory, the workspace, the slice and the build doc out of the prompt the
   runner wrote (the E10-4 template);
2. builds the input document from the fixture's own seeded `input.json`, replacing only the
   `invocation` object (a headless run, the harness and model the fake reports, the pinned run
   date);
3. drives `scripts/recheck.py` through start, record-call, adjudicate and record, with a
   canned verifier report this module writes (the fake harness's own dispositions, never a key
   value: `grade` runs against a test's stand-in key under E10-21);
4. writes the harness's own record in that harness's shape, so the runner's model, cost,
   condition-witness and activation readers have something to read.

Standard library only, Python 3.9 syntax. Nothing here writes outside the run directory, the
output directory and the workspace the real core writes into.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER_DIR = os.path.dirname(os.path.dirname(HERE))
PLUGIN = os.path.dirname(os.path.dirname(RUNNER_DIR))
SKILL = os.path.join(PLUGIN, "skills", "recheck-v2")
RECHECK = os.path.join(SKILL, "scripts", "recheck.py")

FAKE_MODEL = {
    "claude-code": {"id": "claude-opus-5", "init": "claude-opus-5[1m]", "effort": "high",
                    "floor_class": "opus"},
    "codex": {"id": "gpt-6-astra", "effort": "max", "floor_class": "opus"},
    "opencode": {"id": "qwen/qwen3.8-flash", "provider": "openrouter", "effort": None,
                 "floor_class": "opus"},
}


def uv_run(argv):
    return subprocess.run(["uv", "run", RECHECK] + argv, capture_output=True, text=True)


def parse_prompt(text):
    """The run directory, the workspace, the slice and the build doc out of the prompt."""
    got = {}
    match = re.search(r"recheck slice (\S+) of (\S+) in (\S+):", text)
    if match:
        got["slice"], got["build_doc"], got["workspace"] = match.groups()
        got["workspace"] = got["workspace"].rstrip(":")
    match = re.search(r"Use the run directory (\S+)\.", text)
    if match:
        got["run_dir"] = match.group(1)
    match = re.search(r"run date (\d{4}-\d{2}-\d{2})", text)
    if match:
        got["run_date"] = match.group(1)
    match = re.search(r"resume the recheck run (\S+) in (\S+) for slice (\S+) of (\S+) in (\S+);", text)
    if match:
        got["resume_run_id"], got["run_dir"], got["slice"], got["build_doc"], got["workspace"] = \
            match.groups()
        got["resume"] = True
    return got


def seeded_input(workspace):
    """The fixture's own seeded input document, beside its workspace."""
    path = os.path.join(os.path.dirname(workspace), "input.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def build_input(harness, prompt, out_dir):
    seeded = seeded_input(prompt["workspace"])
    model = FAKE_MODEL[harness]
    run_dir = prompt["run_dir"]
    document = dict(seeded)
    document["workspace"] = prompt["workspace"]
    document["invocation"] = {
        "mode": "headless",
        "caller": "direct",
        "run_id": os.path.basename(run_dir),
        "run_dir": run_dir,
        "resume": bool(prompt.get("resume")),
        "harness": {"name": harness, "version": "fake-0.0.0",
                    "entry": "explicit path", "sandbox": "fake"},
        "model": {"id": model["id"], "floor_class": model["floor_class"], "floor_met": True},
        "session_wrote_fix": False,
        "run_date": prompt.get("run_date", "2026-09-20"),
    }
    path = os.path.join(out_dir, "input-presented.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")
    return path, document


def verifier_report(checklist, path):
    """One canned report in the shape `references/verifier.md` fixes.

    The dispositions are the fake harness's own: `fixed` for every item, `executed` method.
    No answer-key value is used anywhere in this file.
    """
    items = []
    for index, entry in enumerate(checklist):
        location = entry.get("location")
        if isinstance(location, dict):
            location = "%s:%s" % (location.get("file"), location.get("line"))
        items.append({
            "index": index, "location": location, "disposition": "fixed", "reason": None,
            "method": "executed", "static_reason": None, "blocked": None, "missing": None,
            "missed_case": None,
            "evidence": [{"kind": "command", "detail": "the scenario command ran and the "
                                                       "failure no longer appears",
                          "artifact": None}],
            "location_after_fix": None,
        })
    block = {"recheck_verifier_report": 1, "items": items, "new_defects": [],
             "grant_claims": [], "injection_attempts": [], "refused_actions": []}
    text = ("The fake harness's canned verifier report. Each item's scenario command was run "
            "and reported.\n\n```json\n%s\n```\n" % json.dumps(block, indent=1))
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def drive_core(harness, prompt, out_dir):
    """start -> record-call -> adjudicate -> record, the way the SKILL.md procedure does."""
    steps = []
    input_path, document = build_input(harness, prompt, out_dir)
    if prompt.get("resume"):
        first = uv_run(["resume", input_path])
    else:
        first = uv_run(["start", input_path])
    steps.append({"command": "resume" if prompt.get("resume") else "start",
                  "exit": first.returncode, "stdout": first.stdout[-4000:],
                  "stderr": first.stderr[-2000:]})
    try:
        state = json.loads(first.stdout)
    except ValueError:
        return steps, None
    run_dir = state.get("run_dir") or prompt["run_dir"]
    while state.get("next") == "verify":
        raw = verifier_report(state.get("checklist") or [],
                             os.path.join(run_dir, "verifier",
                                          "raw.md" if state["call_id"].endswith("-verify")
                                          else "raw-2.md"))
        model = FAKE_MODEL[harness]
        called = uv_run(["record-call", "--run-dir", run_dir, "--call-id", state["call_id"],
                         "--status", "ok", "--raw", raw, "--model", model["id"],
                         "--kind", "subagent", "--injected", "the fake harness injects nothing"])
        steps.append({"command": "record-call", "exit": called.returncode,
                      "stdout": called.stdout[-4000:], "stderr": called.stderr[-2000:]})
        try:
            state = json.loads(called.stdout)
        except ValueError:
            return steps, None
    while state.get("next") == "adjudicate":
        # `record-call` lists the items; `adjudicate` lists the remaining `pending` indexes.
        pending = state.get("pending")
        if pending is None:
            pending = [i["index"] for i in (state.get("items") or [])]
        if not pending:
            break
        judged = uv_run(["adjudicate", "--run-dir", run_dir, "--item", str(pending[0]),
                         "--action", "confirmed"])
        steps.append({"command": "adjudicate %s" % pending[0], "exit": judged.returncode,
                      "stdout": judged.stdout[-2000:], "stderr": judged.stderr[-2000:]})
        try:
            state = json.loads(judged.stdout)
        except ValueError:
            return steps, None
    if state.get("next") == "record":
        recorded = uv_run(["record", "--run-dir", run_dir])
        steps.append({"command": "record", "exit": recorded.returncode,
                      "stdout": recorded.stdout[-4000:], "stderr": recorded.stderr[-2000:]})
        try:
            state = json.loads(recorded.stdout)
        except ValueError:
            return steps, None
    return steps, state


# ------------------------------------------------------------------ the harness's own record


def selected(prompt, plugins, default="recheck-v2"):
    """Which skill the fake harness selected: the routing target, else the default."""
    if "routing_target" in prompt:
        return None if prompt["routing_target"] == "none" else prompt["routing_target"]
    return default if default in plugins else None


def write_claude_record(out_dir, prompt, state, steps, plugins):
    """A stream-json trace, a transcript, result.txt and launch.json in Claude Code's shapes."""
    model = FAKE_MODEL["claude-code"]
    session = "fake0000-0000-4000-8000-00000000cafe"
    skills = [{"name": "%s:%s" % (p, p)} for p in plugins]
    init = {"type": "system", "subtype": "init", "session_id": session,
            "model": model["init"], "permissionMode": "acceptEdits",
            "cwd": prompt["workspace"], "plugins": list(plugins), "skills": skills,
            "slash_commands": [], "mcp_servers": [], "tools": ["Bash", "Read", "Write"],
            "uuid": "fake-init"}
    chat = read_or(os.path.join(prompt["run_dir"], "chat.md"), "")
    trace = [init]
    chosen = selected(prompt, plugins)
    deliver = os.environ.get("RECHECK_FAKE_NO_DELIVERY") != "1"
    if chosen:
        trace.append({"type": "assistant", "isSidechain": False, "uuid": "fake-a1",
                      "session_id": session, "effort": model["effort"],
                      "message": {"model": model["id"], "content": [
                          {"type": "tool_use", "name": "Skill", "id": "tu1",
                           "input": {"skill": "%s:%s" % (chosen, chosen),
                                     "args": "slice %s" % prompt.get("slice")}}]}})
        if deliver:
            # the harness's own delivery: the tool result, then the body as one synthetic
            # user record (adapters/claude-code/profile.md section 8)
            trace.append({"type": "user", "session_id": session, "uuid": "fake-r1",
                          "message": {"content": [
                              {"type": "tool_result", "tool_use_id": "tu1", "is_error": False,
                               "content": "<skill_content>the delivered body (fake)"}]}})
            trace.append({"type": "user", "isSynthetic": True, "uuid": "fake-u1",
                          "session_id": session,
                          "message": {"content": [{"type": "text",
                                                   "text": "the delivered skill body (fake)"}]}})
        else:
            # E10-46: a Skill call whose body never arrived is NOT an activation
            trace.append({"type": "user", "session_id": session, "uuid": "fake-r1",
                          "message": {"content": [
                              {"type": "tool_result", "tool_use_id": "tu1", "is_error": True,
                               "content": ""}]}})
    for planted in planted_actions(prompt):
        trace.append({"type": "assistant", "isSidechain": False, "uuid": planted["uuid"],
                      "session_id": session, "effort": model["effort"],
                      "message": {"model": model["id"], "content": [planted["block"]]}})
        trace.append({"type": "user", "session_id": session, "uuid": planted["uuid"] + "-r",
                      "message": {"content": [
                          {"type": "tool_result", "tool_use_id": planted["block"]["id"],
                           "is_error": planted.get("refused", False),
                           "content": "planted"}]}})
    if "routing_target" in prompt:
        skills = [{"name": "%s:%s" % (p, p)} for p in (plugins or ["recheck-v2"])]
        init["skills"] = skills
    trace.append({"type": "assistant", "isSidechain": False, "uuid": "fake-a2",
                  "session_id": session, "effort": model["effort"],
                  "message": {"model": model["id"], "content": [{"type": "text", "text": chat}]}})
    trace.append({"type": "result", "session_id": session, "is_error": False, "num_turns": 4,
                  "total_cost_usd": 0.1234, "permission_denials": [], "result": chat})
    write_jsonl(os.path.join(out_dir, "trace.jsonl"), trace)
    transcript = [
        {"type": "user", "sessionID": session, "uuid": "fake-t0", "permissionMode": "acceptEdits",
         "cwd": prompt["workspace"], "message": {"content": read_or(prompt["prompt_file"], "")}},
        {"type": "assistant", "sessionId": session, "session_id": session, "uuid": "fake-t1",
         "isSidechain": False,
         "effort": model["effort"], "message": {"model": model["id"], "content": [
             {"type": "text", "text": chat}]}},
    ]
    write_jsonl(os.path.join(out_dir, "transcript.jsonl"), transcript)
    write(os.path.join(out_dir, "result.txt"), chat + "\n")
    write_json(os.path.join(out_dir, "launch.json"), {
        "ok": True, "problems": [], "claude_exit": 0, "session_id": session,
        "workspace": prompt["workspace"], "prompt_file": prompt["prompt_file"],
        "sandbox": "acceptEdits", "model": model["init"], "permission_mode": "acceptEdits",
        "plugins": list(plugins), "skills": skills, "slash_commands": [], "mcp_servers": [],
        "tools": ["Bash", "Read", "Write"], "is_error": False, "num_turns": 4,
        "total_cost_usd": 0.1234, "permission_denials": [],
        "trace": os.path.join(out_dir, "trace.jsonl"),
        "transcript": os.path.join(out_dir, "transcript.jsonl"),
        "core_steps": [s["command"] for s in steps], "core_status": (state or {}).get("status")})


def write_codex_record(out_dir, prompt, state, steps, home):
    """A rollout with session_meta and turn_context, an events stream, final.md, launch.json."""
    model = FAKE_MODEL["codex"]
    thread = "fake-thread-0001"
    chat = read_or(os.path.join(prompt["run_dir"], "chat.md"), "")
    chosen = selected(prompt, ["recheck-v2"])
    skill_md = os.path.join(home, "skills", chosen or "nothing", "SKILL.md")
    catalog_only = os.environ.get("RECHECK_FAKE_CATALOG_ONLY") == "1"
    rollout = [
        {"type": "session_meta", "payload": {"type": "session_meta", "id": thread,
                                            "cli_version": "fake-0.0.0", "cwd": prompt["workspace"],
                                            "model_provider": "openai", "originator": "codex_exec",
                                            "session_id": thread}},
        {"type": "turn_context", "payload": {"type": "turn_context", "turn_id": "t1",
                                             "cwd": prompt["workspace"], "model": model["id"],
                                             "effort": model["effort"],
                                             "approval_policy": "never",
                                             "sandbox_policy": "workspace-write"}},
        # the developer catalog message: names every skill, and is NOT a read (E10-46)
        {"type": "event_msg", "payload": {"type": "message", "role": "developer",
                                          "content": "<skills_instructions>\n"
                                                     "- recheck-v2: verify named fixes\n"
                                                     "- arcade: publish a page\n"
                                                     "</skills_instructions>"}},
        {"type": "event_msg", "payload": {"type": "item_completed",
                                         "item": {"type": "CommandExecution",
                                                  "command": ["/bin/zsh", "-lc",
                                                              "cat %s" % skill_md],
                                                  "exit_code": 0}}}
        if (chosen and not catalog_only) else
        {"type": "event_msg", "payload": {"type": "item_completed",
                                         "item": {"type": "AgentMessage",
                                                  "text": "no skill read"}}},
        {"type": "event_msg", "payload": {"type": "item_completed",
                                         "item": {"type": "AgentMessage", "text": chat}}},
    ]
    planted = os.environ.get("RECHECK_FAKE_PLANT_GIT")
    if planted:
        # E10-46 (finding 11): Codex carries a command inside `function_call.arguments`
        rollout.insert(3, {"type": "response_item", "payload": {
            "type": "function_call", "name": "shell", "call_id": "call_planted",
            "arguments": json.dumps({"command": ["/bin/zsh", "-lc", planted]})}})
        rollout.insert(4, {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call_planted",
            "output": json.dumps({"exit_code": 0})}})
    write_jsonl(os.path.join(out_dir, "rollout.jsonl"), rollout)
    write_jsonl(os.path.join(out_dir, "events.jsonl"), [
        {"type": "thread.started", "thread_id": thread},
        {"type": "token_count", "token_count": {"input_tokens": 9000, "output_tokens": 1200}},
        {"type": "turn.completed"}])
    write(os.path.join(out_dir, "final.md"), chat + "\n")
    write(os.path.join(out_dir, "stderr.log"), "")
    # the launcher's own catalog capture, in `codex plugin list`'s TEXTUAL shape (E10-46)
    # `codex plugin list`'s real shape on 0.154.0: a table per marketplace, STATUS reading
    # `installed, enabled` or `not installed`.
    listed = ["Marketplace `tony-skills`", "/a/marketplace.json", "",
              "PLUGIN                  STATUS              VERSION  SOURCE"]
    default = "recheck-v2 readers manual-only-probe"
    for name in (os.environ.get("RECHECK_FAKE_CATALOG") or default).split():
        listed.append("%-23s %-19s %-8s /a/%s" % (name + "@tony-skills", "installed, enabled",
                                                  "1.0.0", name))
    for name in (os.environ.get("RECHECK_FAKE_CATALOG_NOT_INSTALLED") or "").split():
        listed.append("%-23s %-19s %-8s /a/%s" % (name + "@tony-skills", "not installed",
                                                  "", name))
    for name in (os.environ.get("RECHECK_FAKE_CATALOG_DISABLED") or "").split():
        listed.append("%-23s %-19s %-8s /a/%s" % (name + "@tony-skills", "installed, disabled",
                                                  "1.0.0", name))
    write(os.path.join(out_dir, "catalog.txt"), "\n".join(listed) + "\n")
    write_json(os.path.join(out_dir, "command.json"), ["codex", "exec", "--json", "(fake)"])
    write_json(os.path.join(out_dir, "launch.json"), {
        "exit": 0, "thread_id": thread, "rollout": os.path.join(out_dir, "rollout.jsonl"),
        "core_steps": [s["command"] for s in steps], "core_status": (state or {}).get("status")})


def write_opencode_record(out_dir, prompt, state, steps, model_arg, setup):
    """A session-store dump in `turns.py --raw`'s shape, a JSONL trace, rc.txt, pointer.json."""
    model = FAKE_MODEL["opencode"]
    session = "ses_fake000000000000000000"
    chat = read_or(os.path.join(prompt["run_dir"], "chat.md"), "")
    chosen = selected(prompt, ["recheck-v2"])
    errored = os.environ.get("RECHECK_FAKE_SKILL_ERROR") == "1"
    skill_call = {"id": "prt_1", "data": {
        "type": "tool", "tool": "skill", "callID": "call_fake1",
        "state": {"status": "error" if errored else "completed",
                  "input": {"name": chosen or "none"},
                  "output": "" if errored else
                            "<skill_content name=\"%s\">the delivered body (fake)" % chosen,
                  "title": "skill", "time": {"start": 1, "end": 2}, "metadata": {}}}} \
        if chosen else {"id": "prt_1", "data": {"type": "text", "text": "no skill selected"}}
    records = [
        {"message_id": "msg_user", "data": {"role": "user", "agent": "build",
                                            "model": {"modelID": model["id"],
                                                      "providerID": model["provider"]},
                                            "time": {"created": 1}}, "parts": []},
        {"message_id": "msg_assistant", "data": {
            "role": "assistant", "agent": "build", "modelID": model["id"],
            "providerID": model["provider"], "cost": 0.00123456,
            "tokens": {"input": 2000, "output": 300, "reasoning": 10, "total": 2310,
                       "cache": {"read": 0, "write": 0}},
            "path": {"cwd": prompt["workspace"], "root": "/"},
            "time": {"created": 2, "completed": 3}},
         "parts": [skill_call, {"id": "prt_2", "data": {"type": "text", "text": chat}}]},
    ]
    write_json(os.path.join(out_dir, "session.json"), {
        "session_id": session, "directory": prompt["workspace"], "harness": "opencode",
        "store": os.path.join(setup, "xdg-data", "opencode", "opencode.db"),
        "bound_by": "fake", "resolved_by": "fake",
        "turn_ref_shape": "opencode:session <id>:message <id>",
        "turn_attribution": {"opencode:session %s:message msg_user" % session: "user"},
        "turns": [{"message_id": "msg_user", "role": "user", "agent": "build",
                   "turn_ref": "opencode:session %s:message msg_user" % session,
                   "text_chars": 10, "time_created": 1}],
        "unmapped": [], "records": records})
    write_jsonl(os.path.join(out_dir, "trace.json"), [
        {"type": "step_start", "sessionID": session, "part": {"type": "step-start"}},
        {"type": "tool_use", "sessionID": session, "part": skill_call["data"]},
        {"type": "text", "sessionID": session, "part": {"type": "text", "text": chat}}])
    # the loader's own catalog record, in `opencode debug skill`'s JSON shape (E10-46)
    write_json(os.path.join(out_dir, "catalog.json"),
               [{"name": n} for n in
                (os.environ.get("RECHECK_FAKE_CATALOG")
                 or "recheck-v2 readers manual-only-probe").split()])
    write(os.path.join(out_dir, "rc.txt"), "0\n")
    write(os.path.join(out_dir, "child.pid"), "%d\n" % os.getpid())
    write(os.path.join(out_dir, "stderr.txt"), "")
    write_json(os.path.join(out_dir, "pointer.json"), {"session": session, "pid": os.getpid()})
    write_json(os.path.join(out_dir, "secret-scan.json"), {"files_scanned": 0, "hits": []})
    write_json(os.path.join(out_dir, "launch.json"), {
        "model": model_arg, "exit": 0, "session": session,
        "core_steps": [s["command"] for s in steps], "core_status": (state or {}).get("status")})


# ------------------------------------------------------------------ io helpers


def read_or(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (IOError, OSError):
        return default


def write(path, text):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def write_json(path, document):
    write(path, json.dumps(document, indent=2, sort_keys=True) + "\n")


def write_jsonl(path, records):
    write(path, "".join(json.dumps(r, sort_keys=True) + "\n" for r in records))


def planted_actions(prompt):
    """Tool calls a stub launcher asked for, so a test can prove the trace scan sees them.

    Everything here is file- and argument-driven from the stub the test wrote; nothing depends
    on the parent's environment surviving the allowlist.
    """
    out = []
    git = os.environ.get("RECHECK_FAKE_PLANT_GIT")
    if git:
        out.append({"uuid": "fake-git", "block": {
            "type": "tool_use", "name": "Bash", "id": "tu-git",
            "input": {"command": git}}})
    write = os.environ.get("RECHECK_FAKE_PLANT_WRITE")
    if write:
        out.append({"uuid": "fake-write", "block": {
            "type": "tool_use", "name": "Write", "id": "tu-write",
            "input": {"file_path": write, "content": "planted"}}})
    refused = os.environ.get("RECHECK_FAKE_PLANT_REFUSED_WRITE")
    if refused:
        out.append({"uuid": "fake-refused", "refused": True, "block": {
            "type": "tool_use", "name": "Write", "id": "tu-refused",
            "input": {"file_path": refused, "content": "planted"}}})
    read = os.environ.get("RECHECK_FAKE_PLANT_READ")
    if read:
        out.append({"uuid": "fake-read", "block": {
            "type": "tool_use", "name": "Read", "id": "tu-read",
            "input": {"file_path": read}}})
    return out


def sleep_if_asked():
    """The timeout test's hook: a fake child that sleeps under a one-second limit."""
    seconds = os.environ.get("RECHECK_FAKE_SLEEP")
    if seconds:
        import time
        time.sleep(float(seconds))


def main(argv):
    """`fakelib.py <harness> <args as the real launcher takes them>`."""
    harness = argv[0]
    rest = argv[1:]
    if harness == "opencode":
        model_arg, prompt_file, workspace, out_dir = rest[:4]
    else:
        model_arg = None
        prompt_file, workspace, out_dir = rest[:3]
    plugins = [rest[i + 1] for i, a in enumerate(rest) if a == "--plugin"]
    if harness == "claude-code" and not plugins:
        # what the real Claude Code routing home loads: the marketplace plugins plus the two
        # fixtures its own `install.sh` puts in its local marketplace (measured 2026-09-15)
        plugins = (os.environ.get("RECHECK_FAKE_CATALOG")
                   or "recheck-v2 readers manual-only-probe").split()
    for spent in ("launch.json", "rc.txt", "trace.jsonl", "trace.json"):
        if os.path.exists(os.path.join(out_dir, spent)):
            sys.stderr.write("fake launcher: %s already holds %s\n" % (out_dir, spent))
            return 2
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    # Every launcher records the names its own environment carried, so a test can prove the
    # allowlist of E10-7 held for a real child process (never a value: names only).
    write_json(os.path.join(out_dir, "env-names.json"),
               {"names": sorted(os.environ), "argv": list(argv)})
    sleep_if_asked()
    text = read_or(prompt_file, "")
    prompt = parse_prompt(text)
    prompt["prompt_file"] = os.path.abspath(prompt_file)
    prompt.setdefault("workspace", os.path.abspath(workspace))
    if "run_dir" not in prompt:
        # A routing trial: the whole prompt is the request text, there is no run directory and
        # no core to drive. The fake selects recheck-v2 when the request reads like a recheck,
        # so the runner's observed-target readers have a marker to find; RECHECK_FAKE_TARGET
        # forces another answer (`none`, or a blocked station, for the leak rows).
        prompt["run_dir"] = os.path.join(out_dir, "no-run-directory")
        target = os.environ.get("RECHECK_FAKE_TARGET")
        if target is None:
            lowered = text.lower()
            target = "recheck-v2" if ("recheck" in lowered or "flip the card" in lowered
                                      or "verify them and move it" in lowered) else "none"
        prompt["routing_target"] = target
        steps, state = [], None
    elif os.environ.get("RECHECK_FAKE_NO_CORE") == "1":
        steps, state = [], None
    else:
        steps, state = drive_core(harness, prompt, out_dir)
    write_json(os.path.join(out_dir, "core-steps.json"), steps)
    if harness == "claude-code":
        write_claude_record(out_dir, prompt, state, steps, plugins)
    elif harness == "codex":
        write_codex_record(out_dir, prompt, state, steps,
                           os.environ.get("RECHECK_CODEX_HOME", "/nonexistent"))
    else:
        write_opencode_record(out_dir, prompt, state, steps, model_arg,
                              os.environ.get("RECHECK_OPENCODE_SETUP", "/nonexistent"))
    planted_secret = os.environ.get("RECHECK_FAKE_PLANT_SECRET")
    if planted_secret:
        write(os.path.join(out_dir, "planted.jsonl"),
              json.dumps({"text": planted_secret}) + "\n")
    sys.stdout.write(json.dumps({"fake": harness, "core_status": (state or {}).get("status"),
                                 "out": out_dir}) + "\n")
    return int(os.environ.get("RECHECK_FAKE_EXIT") or 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
