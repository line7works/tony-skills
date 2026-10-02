"""`request`: one readers request per local lens, one per outside row the owner's answer named, and
the one re-send a failed local lens may take (contract sections 3.4 and 3.6; readings CR-5, CR-6, CR-9
and CR-10).

Every request is built by the copied `station_core/readers_request.py`, which decides `authorized` from
the data it is handed and from nothing else: the local requests are handed no owner's word, so they
never carry it; the outside requests are handed the rows the recorded answer named, so it lands on
exactly those rows and never on a Claude row. Before any request is built, readers' identity is read and
checked (`readers_link.py`), and every packet is held to the file list `scope` wrote (each file's sha256,
no file added): a packet that moved is refused (exit 5) and nothing is built.

`request --outside` runs only after `record-local` has completed (exit 5 before it), so no outside
request file exists under the run directory before the local verdict is formed. It refuses (exit 5) a
row the answer did not name, a Claude row the answer named (a Claude row is never an outside reviewer
and never carries `authorized`), and a row suggest reported dropped. The script builds and records; the
executor summons readers.
"""
import os

from station_core import fsio, readers_request

from . import ask as askmod, common, readers_link, report

FLOOR = "opus"
PACKET_ONLY_BUDGET = 32768
RETRYABLE = ("transport-failed", "empty", "incomplete")


def _refuse(ctx, run, reason, **extra):
    return ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"], reason=reason, **extra), 5)


def packet_problems(packet, workspace=True):
    """[message] for every way a packet differs from the list `scope` wrote; [] when it holds. With
    `workspace` false (a re-send, after the first fleet may have run tests in the shared local copy and
    left scratch there), only the mandate and the documents are held to the list."""
    listing = fsio.read_json(packet["files"])
    out = []
    listed = set()
    for entry in listing["files"]:
        listed.add(entry["abs"])
        if not workspace and entry["role"] == "workspace":
            continue
        if not os.path.isfile(entry["abs"]):
            out.append("%s: %s is gone" % (packet["name"], entry["path"]))
        elif fsio.sha256_file(entry["abs"]) != entry["sha256"]:
            out.append("%s: %s changed after scope" % (packet["name"], entry["path"]))
    roots = [listing.get("workspace")] if workspace else []
    for root in roots + [os.path.dirname(d) for d in packet.get("documents") or [] if packet["side"] == "outside"]:
        if not root or not os.path.isdir(root):
            continue
        for base, dirs, files in os.walk(root):
            for name in files:
                full = os.path.join(base, name)
                if full not in listed:
                    out.append("%s: %s was added after scope" % (packet["name"], os.path.relpath(full, root)))
    return sorted(set(out))


def _identity(ctx, run, args):
    found, roster, ident, refusals = readers_link.resolve(run, args.readers_root)
    if refusals:
        readers_link.refused_line(run, ctx, found, ident, refusals)
        report.finish(ctx, run, "stopped", "station-refused",
                      "readers at %s is not the readers this core summons through: %s; nothing was requested"
                      % (found["root"], "; ".join(r["message"] for r in refusals)))
    return found, roster, ident


def handler(ctx, args):
    if args.outside:
        return _outside(ctx, args)
    if args.resend:
        return _resend(ctx, args)
    run = common.open_run(ctx, args.run_dir, ("scoped",), "request")
    return _local(ctx, args, run)


def _local(ctx, args, run):
    scope = common.read(run, "scope.json")
    ask = common.read(run, "ask.json")
    local = [r for r in ask["rows"] if r["side"] == "local"][0]
    session_model = common.station(run).get("session_model")
    if local["row"] == "claude-session" and not session_model:
        return _refuse(ctx, run, "the local lenses run on claude-session, which inherits this session's model: put the "
                       "model id this session's system prompt names in station.session_model; nothing was built")
    found, roster, ident = _identity(ctx, run, args)
    packets = [p for p in scope["packets"] if p["side"] == "local"]
    problems = [m for p in packets for m in packet_problems(p)]
    if problems:
        return _refuse(ctx, run, "a packet moved after scope; nothing was built: %s" % "; ".join(problems),
                       problems=problems)
    calls = [_local_call(run, roster, local, packet, packet["lens"], "%s-local-%s"
                         % (run.checkpoint["run_id"], packet["lens"]), session_model) for packet in packets]
    common.write(run, "requests-local.json", {"readers": {"root": found["root"], "route": found["route"],
                                                          "identity": ident},
                                              "run_dir": common.path_of(run, "readers"), "calls": calls,
                                              "resent": []})
    common.advance(run, "requested-local")
    route = "local lenses through %s with profile %s" % (local["row"], local["profile"])
    if local["profile"] == "repo":
        route += ": each lens reads the code and runs no check, and the Method line says so"
    return ctx.emit(ctx.envelope(next="record-local", run_id=run.checkpoint["run_id"], calls=calls, route=route,
                                 depth_line="depth %s: %s" % (scope["depth"], ", ".join(scope["lenses"])),
                                 readers_run_dir=common.path_of(run, "readers"),
                                 summon="summon /readers with these requests as one fleet under run id %s; then "
                                        "record-local" % run.checkpoint["run_id"]))


def _local_call(run, roster, local, packet, lens, call_id, session_model):
    req = readers_request.build(local["row"], {}, roster, mandate=packet["mandate"], profile=local["profile"],
                                run_id=run.checkpoint["run_id"], call_id=call_id, documents=packet["documents"],
                                workspace=packet["workspace"], session_model=session_model,
                                run_dir=common.path_of(run, "readers"))
    req["floor"] = FLOOR
    path = common.path_of(run, os.path.join("requests", "%s.json" % call_id))
    fsio.write_json(path, req)
    return {"lens": lens, "call_id": call_id, "row": local["row"], "profile": local["profile"], "request_file": path,
            "packet": packet["name"]}


def _resend(ctx, args):
    run = common.open_run(ctx, args.run_dir, ("requested-local",), "request --resend")
    if args.status not in RETRYABLE:
        return _refuse(ctx, run, "a local lens is re-sent once only after %s; %r is deterministic (the same request "
                       "refuses the same way), so the local review is incomplete: record-local with its status"
                       % (", ".join(RETRYABLE), args.status))
    requests = common.read(run, "requests-local.json")
    first = [c for c in requests["calls"] if c["lens"] == args.resend]
    if not first:
        return _refuse(ctx, run, "no local lens %r in this run" % args.resend)
    if args.resend in requests["resent"]:
        return _refuse(ctx, run, "the lens %r was re-sent once already; a second failure leaves the local review "
                       "incomplete" % args.resend)
    scope = common.read(run, "scope.json")
    ask = common.read(run, "ask.json")
    local = [r for r in ask["rows"] if r["side"] == "local"][0]
    packet = [p for p in scope["packets"] if p["name"] == first[0]["packet"]][0]
    problems = packet_problems(packet, workspace=False)
    if problems:
        return _refuse(ctx, run, "the packet moved after scope; nothing was built: %s" % "; ".join(problems))
    found, roster, ident = _identity(ctx, run, args)
    call = _local_call(run, roster, local, packet, args.resend, "%s-2" % first[0]["call_id"],
                       common.station(run).get("session_model"))
    call["resend_of"] = {"call_id": first[0]["call_id"], "status": args.status}
    requests["calls"].append(call)
    requests["resent"].append(args.resend)
    common.write(run, "requests-local.json", requests)
    return ctx.emit(ctx.envelope(next="record-local", run_id=run.checkpoint["run_id"], call=call))


def _outside(ctx, args):
    run = ctx.open_run(args.run_dir)
    phase = run.checkpoint.get("phase")
    if phase != "recorded-local":
        return _refuse(ctx, run, "no outside request before record-local has completed (this run is at %r): the local "
                       "review forms its findings first, independently; nothing was built" % phase)
    ask = common.read(run, "ask.json")
    scope = common.read(run, "scope.json")
    answer = ask["answer"]
    offered = dict((r["row"], r) for r in ask["rows"] if r["side"] == "outside")
    wanted = list(args.row or answer["rows"])
    if not wanted:
        return _refuse(ctx, run, "the owner's answer named no outside row: this is a local-only review; run verdict")
    found, roster, ident = _identity(ctx, run, args)
    refusals = []
    for row in wanted:
        provider = askmod.row_of(roster, row) and askmod.row_of(roster, row).get("provider")
        if row not in answer["rows"]:
            refusals.append("%s: the owner's answer in this run did not name it (%s)" % (row, ", ".join(answer["rows"])
                                                                                       or "no row"))
        elif provider == common.ANTHROPIC or provider is None and row.startswith("claude"):
            refusals.append("%s: a Claude row is never an outside reviewer and never carries authorized; the Claude "
                            "rows are the local fleet" % row)
        elif row not in offered:
            refusals.append("%s: not an outside row this run's ask offered (%s)" % (row, ", ".join(offered)))
        elif not offered[row]["available"]:
            refusals.append("%s: suggest reported it dropped (%s); a dropped row is never sent"
                            % (row, offered[row]["drop_note"] or "unavailable"))
    if refusals:
        return _refuse(ctx, run, "refused before any outside request was built: %s" % "; ".join(refusals),
                       refusals=refusals)
    packets = dict((p["row"], p) for p in scope["packets"] if p["side"] == "outside")
    problems = [m for row in wanted for m in packet_problems(packets[row])]
    if problems:
        return _refuse(ctx, run, "a packet moved after scope; nothing was built: %s" % "; ".join(problems))
    word = {"owner_word": {"rows": list(answer["rows"]), "words": answer["words"]}}
    calls = []
    for row in wanted:
        packet = packets[row]
        call_id = "%s-%s" % (run.checkpoint["run_id"], row)
        req = readers_request.build(row, word, roster, mandate=packet["mandate"], profile=offered[row]["profile"],
                                    run_id=run.checkpoint["run_id"], call_id=call_id,
                                    documents=packet["documents"] or None, workspace=packet["workspace"],
                                    model=(answer.get("models") or {}).get(row), run_dir=common.path_of(run, "readers"))
        if offered[row]["profile"] == "packet-only":
            req["output_budget"] = PACKET_ONLY_BUDGET
        if req.get("authorized") is not True:
            raise RuntimeError("an outside request the owner named came back without authorized: %s" % row)
        path = common.path_of(run, os.path.join("requests", "%s.json" % call_id))
        fsio.write_json(path, req)
        calls.append({"lens": None, "call_id": call_id, "row": row, "profile": offered[row]["profile"],
                      "request_file": path, "packet": packet["name"], "authorized": True})
    common.write(run, "requests-outside.json", {"readers": {"root": found["root"], "route": found["route"],
                                                            "identity": ident},
                                                "run_dir": common.path_of(run, "readers"), "calls": calls})
    common.advance(run, "requested-outside")
    return ctx.emit(ctx.envelope(next="record-outside", run_id=run.checkpoint["run_id"], calls=calls,
                                 summon="summon /readers with these requests as one fleet under run id %s; each "
                                        "carries authorized on the owner's word in this run; then record-outside"
                                        % run.checkpoint["run_id"]))
