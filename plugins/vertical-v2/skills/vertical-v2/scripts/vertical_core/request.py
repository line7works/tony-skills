"""`request`: one readers request per local lens, one per outside row the owner's answer named, and
the one re-send a failed local lens may take (contract sections 3.4 and 3.6; readings CR-5, CR-6, CR-9
and CR-10; the design round's A4).

Every request is built by the copied `station_core/readers_request.py`, which decides `authorized` from
the data it is handed and from nothing else: the local requests are handed no owner's word, so they
never carry it; the outside requests are handed the rows the recorded answer named, so it lands on
exactly those rows and never on a Claude row. Before any request is built, readers' root is screened and
its identity read and checked (`readers_link.py`).

Every summons gets a FRESH copy (A4, class (a)): the first send and every retry alike, `request` reads the
reviewed commit through `packet.Snapshot`, has `packet.build` decide the packet, cuts it into
`summons/<call id>/` (a directory that must not exist yet, under a `summons` folder that is no link and lies
inside the run directory, else a refusal before any copy is written, C1A5-3), and, immediately before the
request files are written, holds every cut to that function's own output file by file (`packet.check`:
path, size, sha256) and to the fingerprint `scope` recorded (`packet.digest`). Any difference is refused
(exit 5): the copies this command cut are removed and no request file is written. A reader's scratch, or
anything planted in an earlier copy or in `scope`'s preview, never reaches a later summons.

`request --outside` releases nothing unless the local review is on record as `record-local` wrote it
(A4, class (b)): the checkpoint at `recorded-local` AND the receipt (`record.local_receipt_problem`:
present, valid, naming exactly this run's requested local calls, every hash in it matching the files on
disk now, the record it covers still holding); otherwise exit 5 before any outside file is written. It
refuses (exit 5) a row the answer did not name, a Claude row the answer named (a Claude row is never an
outside reviewer and never carries `authorized`), a row named twice (C1A2-2), and a `--row` subset that
leaves out a named row suggest reported available (C1A2-1: one command sends every named survivor). A
named row suggest reported dropped is never sent: it is recorded in `requests-outside.json` with its
status (`dropped at suggest`) and suggest's reason, and the run continues with the survivors (C1A-1, v1's
"survivors continue"); when every named row was dropped, nothing is summoned and the run moves straight to
the verdict, which names each dropped row. The script builds and records; the executor summons readers.
"""
import os
import shutil

from station_core import fsio, readers_request

from . import ask as askmod, common, packet, readers_link, record, report

FLOOR = "opus"
PACKET_ONLY_BUDGET = 32768
RETRYABLE = ("transport-failed", "empty", "incomplete")


def _refuse(ctx, run, reason, **extra):
    return ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"], reason=reason, **extra), 5)


def _identity(ctx, run, args):
    found, roster, ident, refusals = readers_link.resolve_or_stop(ctx, run, args.readers_root)
    if refusals:
        readers_link.refused_line(run, ctx, found, ident, refusals)
        report.finish(ctx, run, "stopped", "station-refused",
                      "readers at %s is not the readers this core summons through: %s; nothing was requested"
                      % (found["root"], "; ".join(r["message"] for r in refusals)))
    return found, roster, ident


def summons_problem(run):
    """A sentence when the run directory's `summons` folder is a link, is not a folder, or resolves outside the
    run directory (C1A5-3); None when it is absent or a real folder inside it."""
    summons = common.path_of(run, "summons")
    if os.path.islink(summons):
        return ("the run directory's summons folder is a link, so a copy cut there would land wherever it points; "
                "the run refuses and no copy was cut")
    if not os.path.lexists(summons):
        return None
    top = os.path.realpath(run.run_dir).rstrip(os.sep) + os.sep
    if not os.path.isdir(summons) or not os.path.realpath(summons).startswith(top):
        return ("the run directory's summons entry is not a folder inside the run directory; the run refuses and "
                "no copy was cut")
    return None


def fresh_copies(ctx, run, pairs):
    """Cut one fresh packet per (scope's packet, call id) from the reviewed commit, each held to the
    builder's own output and to scope's fingerprint. Returns ({call id: paths}, [problem]); on a problem
    every copy cut here is removed. A `summons` folder that is a link, or that resolves outside the run
    directory, is a problem before any copy is written (C1A5-3)."""
    problem = summons_problem(run)
    if problem:
        return {}, [problem]
    gate = common.read(run, "gate.json")
    scope = common.read(run, "scope.json")
    snap = packet.Snapshot(common.workspace(run), gate["head"], gate["doc"])
    out, problems, cut, built_of = {}, [], [], {}
    for planned, call_id in pairs:
        spec = dict((k, planned.get(k)) for k in ("name", "side", "lens", "row", "profile"))
        built = packet.build(snap, spec, gate, ctx.skill_root, scope["worktree"])
        if packet.digest(built) != planned.get("digest"):
            problems.append("%s: the packet the reviewed commit gives now is not the one scope recorded" % planned["name"])
            continue
        dest = common.path_of(run, os.path.join("summons", call_id))
        if os.path.lexists(dest):
            problems.append("%s: a copy for the call %s exists already; a call id is single-use and every summons "
                            "gets a fresh copy" % (planned["name"], call_id))
            continue
        out[call_id] = packet.cut(built, dest)
        cut.append(dest)
        built_of[call_id] = built
    for call_id, built in built_of.items():
        problems += ["%s: %s" % (call_id, m) for m in packet.check(built, out[call_id]["dir"])]
    if problems:
        for dest in cut:
            shutil.rmtree(dest, ignore_errors=True)
    return out, problems


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
    planned = [p for p in scope["packets"] if p["side"] == "local"]
    pairs = [(p, "%s-local-%s" % (run.checkpoint["run_id"], p["lens"])) for p in planned]
    copies, problems = fresh_copies(ctx, run, pairs)
    if problems:
        return _refuse(ctx, run, "a fresh copy was refused; nothing was built: %s"
                       % "; ".join(problems), problems=problems)
    calls = [_local_call(run, roster, local, p, copies[call_id], call_id, session_model) for p, call_id in pairs]
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


def _local_call(run, roster, local, planned, copy, call_id, session_model):
    req = readers_request.build(local["row"], {}, roster, mandate=copy["mandate"], profile=local["profile"],
                                run_id=run.checkpoint["run_id"], call_id=call_id, documents=copy["documents"],
                                workspace=copy["workspace"], session_model=session_model,
                                run_dir=common.path_of(run, "readers"))
    req["floor"] = FLOOR
    path = common.path_of(run, os.path.join("requests", "%s.json" % call_id))
    fsio.write_json(path, req)
    return {"lens": planned["lens"], "call_id": call_id, "row": local["row"], "profile": local["profile"],
            "request_file": path, "packet": planned["name"], "copy": copy["dir"]}


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
    planned = [p for p in scope["packets"] if p["name"] == first[0]["packet"]][0]
    found, roster, ident = _identity(ctx, run, args)
    call_id = "%s-2" % first[0]["call_id"]
    copies, problems = fresh_copies(ctx, run, [(planned, call_id)])
    if problems:
        return _refuse(ctx, run, "a fresh copy was refused; nothing was built: %s"
                       % "; ".join(problems), problems=problems)
    call = _local_call(run, roster, local, planned, copies[call_id], call_id, common.station(run).get("session_model"))
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
    problem = record.local_receipt_problem(ctx, run)
    if problem:
        return _refuse(ctx, run, "no outside request before the local verdict is on record as record-local wrote it: "
                       "%s; nothing was built" % problem)
    ask = common.read(run, "ask.json")
    scope = common.read(run, "scope.json")
    answer = ask["answer"]
    offered = dict((r["row"], r) for r in ask["rows"] if r["side"] == "outside")
    wanted = list(args.row or answer["rows"])
    if not wanted:
        return _refuse(ctx, run, "the owner's answer named no outside row: this is a local-only review; run verdict")
    twice = sorted(set(row for row in wanted if wanted.count(row) > 1))
    if twice:
        return _refuse(ctx, run, "a row named twice (%s): one request per row, and a call id is single-use; nothing "
                       "was built" % ", ".join(twice))
    refusals = []
    for row in wanted:
        provider = offered.get(row, {}).get("provider")
        if row not in answer["rows"]:
            refusals.append("%s: the owner's answer in this run did not name it (%s)" % (row, ", ".join(answer["rows"])
                                                                                       or "no row"))
        elif provider == common.ANTHROPIC or provider is None and row.startswith("claude"):
            refusals.append("%s: a Claude row is never an outside reviewer and never carries authorized; the Claude "
                            "rows are the local fleet" % row)
        elif row not in offered:
            refusals.append("%s: not an outside row this run's ask offered (%s)" % (row, ", ".join(offered)))
    if refusals:
        return _refuse(ctx, run, "refused before any outside request was built: %s" % "; ".join(refusals),
                       refusals=refusals)
    left = [row for row in answer["rows"] if row not in wanted and offered.get(row, {}).get("available")]
    if left:
        return _refuse(ctx, run, "one request --outside sends every outside row the owner named that suggest reported "
                       "available; --row leaves out %s; nothing was built" % ", ".join(left))
    dropped = [{"row": row, "status": askmod.DROPPED_AT_SUGGEST, "reason": offered[row]["drop_note"] or "unavailable"}
               for row in wanted if not offered[row]["available"]]
    wanted = [row for row in wanted if offered[row]["available"]]
    if not wanted:
        common.write(run, "requests-outside.json", {"readers": None, "run_dir": common.path_of(run, "readers"),
                                                    "calls": [], "dropped": dropped})
        common.write(run, "outside.json", {"calls": [], "findings": [], "ledger_notes": None})
        common.advance(run, "recorded-outside")
        return ctx.emit(ctx.envelope(next="verdict", run_id=run.checkpoint["run_id"], calls=[], dropped=dropped,
                                     summon="nothing to summon: every outside row the owner named was dropped at "
                                            "suggest, and each is recorded with its reason; run verdict"))
    found, roster, ident = _identity(ctx, run, args)
    planned = dict((p["row"], p) for p in scope["packets"] if p["side"] == "outside")
    pairs = [(planned[row], "%s-%s" % (run.checkpoint["run_id"], row)) for row in wanted]
    copies, problems = fresh_copies(ctx, run, pairs)
    if problems:
        return _refuse(ctx, run, "a fresh copy was refused; nothing was built: %s"
                       % "; ".join(problems), problems=problems)
    word = {"owner_word": {"rows": list(answer["rows"]), "words": answer["words"]}}
    calls = []
    for row, (p, call_id) in zip(wanted, pairs):
        copy = copies[call_id]
        req = readers_request.build(row, word, roster, mandate=copy["mandate"], profile=offered[row]["profile"],
                                    run_id=run.checkpoint["run_id"], call_id=call_id,
                                    documents=copy["documents"] or None, workspace=copy["workspace"],
                                    model=(answer.get("models") or {}).get(row), run_dir=common.path_of(run, "readers"))
        if offered[row]["profile"] == "packet-only":
            req["output_budget"] = PACKET_ONLY_BUDGET
        if req.get("authorized") is not True:
            raise RuntimeError("an outside request the owner named came back without authorized: %s" % row)
        path = common.path_of(run, os.path.join("requests", "%s.json" % call_id))
        fsio.write_json(path, req)
        calls.append({"lens": None, "call_id": call_id, "row": row, "profile": offered[row]["profile"],
                      "request_file": path, "packet": p["name"], "copy": copy["dir"], "authorized": True})
    common.write(run, "requests-outside.json", {"readers": {"root": found["root"], "route": found["route"],
                                                            "identity": ident},
                                                "run_dir": common.path_of(run, "readers"), "calls": calls,
                                                "dropped": dropped})
    common.advance(run, "requested-outside")
    return ctx.emit(ctx.envelope(next="record-outside", run_id=run.checkpoint["run_id"], calls=calls, dropped=dropped,
                                 summon="summon /readers with these requests as one fleet under run id %s; each "
                                        "carries authorized on the owner's word in this run; then record-outside"
                                        % run.checkpoint["run_id"]))
