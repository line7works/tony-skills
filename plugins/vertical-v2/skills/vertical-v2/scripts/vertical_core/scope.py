"""`scope`: the archive copies, the spec, the cold packets and their lists (contract section 3.3;
readings CR-3 and CR-4; ruling E15-8 with A2's Q1).

Two copies of the reviewed head are cut by `git archive` under the run directory, each with no `.git`
(no history, no commit message): `export/`, the outside reviewers' workspace, and `local/`, the local
lenses' workspace (a lens that runs tests may write there; the export stays as it was cut). Both leave
out `docs/reviews/`, `docs/records/` and `REVIEW.md`; both drop the builder's notes (a file whose
name, lower-cased with its extension and its separators removed, holds `buildernotes` or `buildnotes`);
and in both the build doc's copy is the spec (`spec.py`). Untracked and ignored files are physically
absent, since the archive holds only the commit's tracked files. vertical-v2 never runs `git worktree`.

One packet per local lens and per outside row the owner's answer named, each a directory under
`packets/` holding its mandate (and, for a packet-only row, the export's UTF-8 files staged with every
`/` written `__`), with two lists written now, before any request: `files.json` (every file the reviewer
receives, workspace and documents alike, each with its sha256 and size) and `withheld.json` (everything
kept back, named: each prior verdict, each records log, the builder's notes, the removed ledger sections
and `Status:` lines, every untracked and ignored path, every working-tree change; and on an outside
packet, `REVIEW.md`, which reaches the local lenses only). `request` holds each packet to its list.
"""
import os
import re
import shutil

from station_core import driver, fsio, validate

from . import ask as askmod, common, gitio, sheet as sheetmod, spec as specmod

EXCLUDED = ("docs/reviews", "docs/records", "REVIEW.md")
SLOTS = ("[BUILD_DOC]", "[BASE_COMMIT]", "[BOUNDARY_FILES]")
NOTES = re.compile(r"build(?:er)?notes")


def builder_notes(path):
    """Whether a file's name declares it the builder's notes."""
    name = os.path.basename(path).lower()
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return NOTES.search(re.sub(r"[-_. ]", "", stem)) is not None


def boundary_lines(boundary):
    out = []
    for row in boundary:
        if row.get("from"):
            out.append("%s\t%s -> %s" % (row["status"], row["from"], row["path"]))
        else:
            out.append("%s\t%s" % (row["status"], row["path"]))
    return "\n".join(out)


def _copy(ws, head, dest, doc, spec_text):
    """Cut one archive copy, drop the builder's notes, and put the spec in the build doc's place."""
    names = gitio.archive_into(ws, head, dest, EXCLUDED)
    notes = [n for n in names if builder_notes(n)]
    for name in notes:
        os.remove(os.path.join(dest, name))
    if doc in names:
        with open(os.path.join(dest, doc), "w", encoding="utf-8", newline="") as fh:
            fh.write(spec_text)
    return sorted(set(names) - set(notes)), notes


def _tracked_under(ws, head, folder):
    return sorted(p for p in gitio.text(ws, ["ls-tree", "-r", "-z", "--name-only", head, "--", folder]).split("\0") if p)


def file_entry(path, rel, role):
    return {"path": rel, "abs": path, "sha256": fsio.sha256_file(path), "size": os.path.getsize(path), "role": role}


def workspace_files(root):
    out = []
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(base, name)
            out.append(file_entry(full, os.path.relpath(full, root), "workspace"))
    return out


def _stage(export, dest):
    """The export's UTF-8 text files staged for a packet-only row; (staged paths, the files left out)."""
    staged, left = [], []
    for base, dirs, files in os.walk(export):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, export)
            with open(full, "rb") as fh:
                data = fh.read()
            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                left.append(rel)
                continue
            target = os.path.join(dest, rel.replace(os.sep, "__"))
            fsio.atomic_write(target, data)
            staged.append(target)
    return staged, left


def lens_brief(skill_root, lens):
    path = os.path.join(validate.references_dir(skill_root), "lens-briefs.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    marker = "\n## %s\n" % lens
    start = text.find(marker)
    if start < 0:
        raise driver.Defect("references/lens-briefs.md has no brief for the lens %r" % lens)
    body = text[start + len(marker):]
    stop = body.find("\n## ")
    return (body if stop < 0 else body[:stop]).strip()


def local_mandate(skill_root, lens, gate, sheet):
    lines = ["# Vertical review: one local lens", "",
             "lens: %s" % lens, "",
             lens_brief(skill_root, lens), "",
             "## The scope", "",
             "The whole vertical: every slice of the build doc, reviewed together against its base.",
             "Base commit: %s" % gate["base"]["commit"], "Head commit: %s" % gate["head"], "",
             "Files this build touched (git diff --name-status <base>..HEAD):", "",
             boundary_lines(gate["boundary"]), "",
             "## What you have", "",
             "- The workspace: a copy of the reviewed head, its tracked files only, with no history. You may run "
             "the project's tests there; write only to scratch and ignored caches, never a tracked file, and report "
             "\"verification blocked\" for a check the sandbox stopped.",
             "- spec.md: the build doc as the spec. It is the only source of requirements; its ledger (the review "
             "record, the handoff notes and the slices' status lines) is left out on purpose, so grade the code "
             "against the spec and never against what an earlier review concluded."]
    if sheet["state"] == "read":
        lines.append("- REVIEW.md: the repo's inspection sheet. Its severity bar grades every defect you report, and "
                     "each repo-specific check below is an item you try to break and report as held or as a finding.")
        if sheet["checks"]:
            lines += ["", "Repo-specific checks:"] + ["- %s" % c for c in sheet["checks"]]
    lines += ["", "## How to report", "",
              "Report every finding, low-confidence ones included; filtering is not yours. Each finding: a claim (one "
              "sentence), its location as file:line in the workspace, a concrete failure scenario, a severity "
              "(BLOCKER: a spec requirement unmet, or a defect that loses data, corrupts state or breaks a shipped "
              "feature; MAJOR: a real defect with a concrete failure path, contained and fixable in place; MINOR: a "
              "rough edge, a missing guard, a thin test), and your confidence (high, medium or low). A concern you "
              "cannot pin to a file and a line goes under \"Concerns without location\".",
              "", "End with what you tried to break and could not, each with how (executed, read or reasoned) and, "
              "for an executed check, what it printed. A review with no findings is a claim that you tried; make it "
              "only after trying."]
    return "\n".join(lines) + "\n"


def outside_mandate(skill_root, spec_text, gate):
    path = os.path.join(validate.skill_root(skill_root), "assets", "vertical-mandate.md")
    with open(path, encoding="utf-8", newline="") as fh:
        body = fh.read()
    for slot, value in zip(SLOTS, (spec_text.rstrip("\n"), gate["base"]["commit"], boundary_lines(gate["boundary"]))):
        if body.count(slot) != 1:
            raise driver.Defect("assets/vertical-mandate.md holds %d %s slot(s), not one" % (body.count(slot), slot))
        body = body.replace(slot, value)
    return body


def handler(ctx, args):
    """`scope --run-dir D`."""
    run = common.open_run(ctx, args.run_dir, ("asked",), "scope")
    gate = common.read(run, "gate.json")
    ask = common.read(run, "ask.json")
    ws = common.workspace(run)
    doc, head = gate["doc"], gate["head"]
    doc_text = gitio.run(ws, ["show", "%s:%s" % (head, doc)]).stdout.decode("utf-8")
    spec_text, removed = specmod.clean(doc_text)
    export = common.path_of(run, "export")
    local = common.path_of(run, "local")
    exported, notes = _copy(ws, head, export, doc, spec_text)
    _copy(ws, head, local, doc, spec_text)
    spec_path = common.path_of(run, "spec.md")
    fsio.atomic_write(spec_path, spec_text.encode("utf-8"))
    sheet = sheetmod.read(ws)
    sheet_path = None
    if sheet["state"] == "read":
        sheet_path = common.path_of(run, "REVIEW.md")
        fsio.atomic_write(sheet_path, sheet["text"].encode("utf-8"))
    depth = common.station(run).get("depth") or "LEAN"
    lenses = sheetmod.lenses(depth, sheet)
    withheld = [{"what": p, "why": "a prior verdict (docs/reviews/)"} for p in _tracked_under(ws, head, "docs/reviews")]
    withheld += [{"what": p, "why": "the records log (docs/records/)"} for p in _tracked_under(ws, head, "docs/records")]
    withheld += [{"what": p, "why": "the builder's notes"} for p in notes]
    for item in removed:
        label = item["what"] if item["what"] != "Status: line" else "Status: line %d" % item["lines"][0]
        withheld.append({"what": "%s %s" % (doc, label),
                         "why": "the build doc's ledger, lines %d to %d (E15-8)" % tuple(item["lines"])})
    withheld += [{"what": p, "why": "untracked: not in the reviewed commit"} for p in gitio.untracked(ws)]
    withheld += [{"what": p, "why": "ignored: not in the reviewed commit"} for p in gitio.ignored(ws)]
    untracked = set(gitio.untracked(ws))
    withheld += [{"what": p, "why": "a working-tree change: the copy holds the reviewed commit's bytes"}
                 for p in (gate.get("dirt") or {}).get("inside", []) + (gate.get("dirt") or {}).get("outside", [])
                 if p not in untracked and not p.endswith("/")]
    sheet_withheld = {"what": "REVIEW.md", "why": "the repo's inspection sheet: the local lenses only (its checks "
                      "are distilled from prior verdicts)"}
    packets = []
    for lens in lenses:
        name = "local-%s" % lens
        folder = common.path_of(run, os.path.join("packets", name))
        mandate = os.path.join(folder, "mandate.md")
        fsio.atomic_write(mandate, local_mandate(ctx.skill_root, lens, gate, sheet).encode("utf-8"))
        documents = [spec_path] + ([sheet_path] if sheet_path else [])
        packets.append(_packet(name, "local", folder, local, documents, mandate, withheld, lens=lens))
    rows = dict((r["row"], r) for r in ask["rows"])
    named = [r for r in ask["answer"]["rows"] if r in askmod.OUTSIDE_ROWS and r in rows]
    if named:
        mandate = common.path_of(run, "mandate.md")
        fsio.atomic_write(mandate, outside_mandate(ctx.skill_root, spec_text, gate).encode("utf-8"))
        for row in named:
            name = "outside-%s" % row
            folder = common.path_of(run, os.path.join("packets", name))
            os.makedirs(folder, exist_ok=True)
            withheld_here = withheld + ([sheet_withheld] if sheet["state"] != "absent" else [])
            if rows[row]["profile"] == "repo":
                packets.append(_packet(name, "outside", folder, export, [], mandate, withheld_here, row=row))
            else:
                staged, left = _stage(export, os.path.join(folder, "files"))
                packets.append(_packet(name, "outside", folder, None, staged, mandate, withheld_here, row=row,
                                       left_out=left))
    scope = {"depth": depth, "lenses": lenses, "export": export, "local": local, "spec": spec_path,
             "removed": removed, "exported": exported,
             "review_sheet": {"state": sheet["state"], "skipped": sheet["skipped"], "checks": sheet["checks"],
                              "unknown": sheet["unknown"], "bar": sheet["bar"], "path": sheet_path},
             "mandate": common.path_of(run, "mandate.md") if named else None, "packets": packets}
    common.write(run, "scope.json", scope)
    common.advance(run, "scoped")
    return ctx.emit(ctx.envelope(next="request", run_id=run.checkpoint["run_id"], depth=depth, lenses=lenses,
                                 review_sheet=sheet["state"], packets=[p["name"] for p in packets],
                                 depth_line="depth %s: %s" % (depth, ", ".join(lenses))))


def _packet(name, side, folder, workspace, documents, mandate, withheld, lens=None, row=None, left_out=()):
    os.makedirs(folder, exist_ok=True)
    files = workspace_files(workspace) if workspace else []
    files += [file_entry(d, os.path.basename(d), "document") for d in documents]
    files.append(file_entry(mandate, "mandate.md", "mandate"))
    listing = {"packet": name, "side": side, "workspace": workspace, "files": files}
    fsio.write_json(os.path.join(folder, "files.json"), listing)
    fsio.write_json(os.path.join(folder, "withheld.json"), {"packet": name, "withheld": withheld,
                                                            "left_out": list(left_out)})
    return {"name": name, "side": side, "lens": lens, "row": row, "dir": folder, "workspace": workspace,
            "documents": list(documents), "mandate": mandate, "files": os.path.join(folder, "files.json"),
            "withheld": os.path.join(folder, "withheld.json"), "left_out": list(left_out)}
