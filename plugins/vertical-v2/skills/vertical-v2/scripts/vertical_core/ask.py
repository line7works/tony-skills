"""`ask`: the two `suggest` calls in v1's order, the ask rendered, the owner's answer recorded
(contract section 3.2; v1's Step 2).

Three modes, one phase:

    ask --run-dir D                                    the two suggest commands, in order
    ask --run-dir D --local-suggest F --outside-suggest G   the ask, rendered from suggest's own output
    ask --run-dir D --answer FILE                      the owner's answer: the rows he named, his words

The local row first, alone, under the floor the local calls carry (`--floor opus`), so a remembered
typed pick on it is dropped before the run freezes; then the outside rows with no floor. Both carry this
run's id and its readers run directory, so they share one snapshot. The script prints the commands and
never runs readers (ruling E15-4); the roster it reads is found through `readers_link.py`, whose
preflight refuses a v1 readers root before any of its files is opened (B5). The local row is `claude-session` on Claude Code and the portable
`claude-opus-cli` on Codex (ruling E15-12); its profile is `repo-with-tools` where the row offers it and
`repo` otherwise, and the ask then says the local lenses run no check. The answer applies to this run
only; nothing is remembered between runs, and nothing after the ask runs until it is recorded.
"""
from station_core import driver, validate

from . import common, readers_link

OUTSIDE_ROWS = ("gpt-astra", "gpt-sol", "gemini", "deepseek", "qwen")
FLOOR = "opus"
DROPPED_AT_SUGGEST = "dropped at suggest"
QUESTION = ("Local-only review, or local + outside reviewers? (Recommended: local + GPT + Gemini. Outside reviewers "
            "see the full tracked code.)")


def local_row(run):
    return "claude-opus-cli" if common.harness(run) == "codex-cli" else "claude-session"


def row_of(rost, row_id):
    for entry in (rost or {}).get("rows") or []:
        if isinstance(entry, dict) and entry.get("id") == row_id:
            return entry
    return None


def profile_for(rost, row_id, local):
    entry = row_of(rost, row_id) or {}
    supported = entry.get("supported_profiles") or []
    if local:
        return "repo-with-tools" if "repo-with-tools" in supported else "repo"
    return "repo" if "repo" in supported else "packet-only"


def dropped_named(ask):
    """[{"row", "status", "reason"}] for each outside row the owner's recorded answer named that suggest
    reported dropped: never sent, recorded with its reason, named in the verdict (C1A-1)."""
    answer = ask.get("answer") or {}
    named = set(answer.get("rows") or [])
    return [{"row": r["row"], "status": DROPPED_AT_SUGGEST, "reason": r.get("drop_note") or "unavailable"}
            for r in ask.get("rows") or [] if r.get("side") == "outside" and r["row"] in named and not r.get("available")]


def commands(run):
    run_id = run.checkpoint["run_id"]
    readers_dir = common.path_of(run, "readers")
    return [{"what": "the local row alone, under the floor the local calls carry",
             "argv": ["suggest", local_row(run), "--run", run_id, "--run-dir", readers_dir, "--floor", FLOOR]},
            {"what": "the outside rows, with no floor",
             "argv": ["suggest", ",".join(OUTSIDE_ROWS), "--run", run_id, "--run-dir", readers_dir]}]


def _refuse(ctx, run, reason):
    return ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"], reason=reason), 5)


def _suggestions(doc, rows):
    by_row = dict((s.get("row"), s) for s in doc.get("suggestions") or [] if isinstance(s, dict))
    return [by_row.get(r) for r in rows]


def render(rows):
    lines = [QUESTION, ""]
    for row in rows:
        what = ("local, always; needs no word" if row["side"] == "local" else
                "outside; needs the owner's word naming the row")
        line = "- %s: model %s, profile %s; %s" % (row["row"], row["model"], row["profile"], what)
        if row["side"] == "local" and row["profile"] == "repo":
            line += ("; on this route each local lens reads the code and runs no check (the row offers no "
                     "tool-running profile), and the verdict's Method line says so")
        if row["side"] == "local":
            line += "; under the floor %s" % FLOOR
        if not row["available"]:
            line += "; dropped: %s" % (row["drop_note"] or "unavailable")
        elif row["drop_note"]:
            line += "; %s" % row["drop_note"]
        lines.append(line)
    lines += ["", "An answer names each row (a bare 'outside' or 'both' is asked again); it applies to this run only."]
    return "\n".join(lines) + "\n"


def handler(ctx, args):
    """`ask --run-dir D [--local-suggest F --outside-suggest G | --answer FILE] [--readers-root DIR]`."""
    if args.answer:
        return _answer(ctx, args)
    run = common.open_run(ctx, args.run_dir, ("gated", "asking"), "ask")
    if bool(args.local_suggest) != bool(args.outside_suggest):
        raise driver.Usage("pass both --local-suggest and --outside-suggest, the two suggest outputs, or neither")
    if not args.local_suggest:
        return ctx.emit(ctx.envelope(next="ask --local-suggest FILE --outside-suggest FILE",
                                     run_id=run.checkpoint["run_id"], suggest=commands(run),
                                     summon="run readers' suggest with each argv, in this order, under this run's id; "
                                            "save each output as a file and pass both back"))
    found, rost = readers_link.find_or_stop(ctx, run, args.readers_root)
    local_doc = common.load_json_file(args.local_suggest, "local suggest")
    outside_doc = common.load_json_file(args.outside_suggest, "outside suggest")
    run_id = run.checkpoint["run_id"]
    for label, doc in (("local", local_doc), ("outside", outside_doc)):
        if doc.get("run_id") != run_id:
            return _refuse(ctx, run, "the %s suggest output is for run %r, not this run %r: run suggest under this run's id"
                           % (label, doc.get("run_id"), run_id))
    if local_doc.get("floor") != FLOOR:
        return _refuse(ctx, run, "the local suggest ran with floor %r: run it with --floor %s, before the outside rows"
                       % (local_doc.get("floor"), FLOOR))
    if outside_doc.get("floor"):
        return _refuse(ctx, run, "the outside suggest ran with a floor (%r): the outside calls carry none, so run it "
                       "without one" % outside_doc.get("floor"))
    local = _suggestions(local_doc, [local_row(run)])
    outside = _suggestions(outside_doc, OUTSIDE_ROWS)
    missing = [r for r, s in zip([local_row(run)], local) if s is None] + [r for r, s in zip(OUTSIDE_ROWS, outside) if s is None]
    if missing:
        return _refuse(ctx, run, "the suggest outputs name no suggestion for %s: run the two suggest commands this "
                       "phase printed" % ", ".join(missing))
    rows = []
    for side, ids, suggestions in (("local", [local_row(run)], local), ("outside", OUTSIDE_ROWS, outside)):
        for row_id, suggestion in zip(ids, suggestions):
            rows.append({"row": row_id, "side": side, "model": suggestion.get("model"),
                         "available": suggestion.get("available") is not False,
                         "drop_note": suggestion.get("drop_note"),
                         "profile": profile_for(rost, row_id, side == "local"),
                         "provider": (row_of(rost, row_id) or {}).get("provider")})
    text = render(rows)
    common.write(run, "ask.json", {"suggest": {"local": local_doc, "outside": outside_doc}, "rows": rows,
                                   "readers": {"root": found["root"], "route": found["route"]}, "ask": text,
                                   "answer": None})
    common.advance(run, "asking")
    return ctx.emit(ctx.envelope(next="ask --answer", run_id=run_id, ask=text, rows=rows,
                                 wait="ask the owner and wait for his answer; silence never proceeds and the "
                                      "recommendation is not a trigger"))


def _answer(ctx, args):
    run = common.open_run(ctx, args.run_dir, ("asking",), "ask --answer")
    doc = common.load_json_file(args.answer, "answer")
    errors = validate.errors_for(doc, common.schema("answer.schema.json", ctx), ctx.prefix)
    if not errors and doc.get("kind") != "ask":
        errors = [{"path": "/kind", "message": "`ask --answer` records the owner's answer to the ask (kind ask)"}]
    if errors:
        return ctx.emit(ctx.envelope(ok=False, error="invalid", run_id=run.checkpoint["run_id"], errors=errors,
                                     reason="the answer does not validate against references/answer.schema.json; "
                                            "nothing was written"), 4)
    if doc["run_id"] != run.checkpoint["run_id"]:
        return _refuse(ctx, run, "the answer is for run %r, not this run %r: an answer applies to its own run only"
                       % (doc["run_id"], run.checkpoint["run_id"]))
    ask = common.read(run, "ask.json")
    ask["answer"] = {"rows": list(doc["rows"]), "words": doc["words"], "models": dict(doc.get("models") or {}),
                     "at": common.now()}
    common.write(run, "ask.json", ask)
    common.advance(run, "asked")
    return ctx.emit(ctx.envelope(next="scope", run_id=run.checkpoint["run_id"], rows=doc["rows"], words=doc["words"]))
