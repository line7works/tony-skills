"""The one packet builder (the E15 lane contract A4, class (a); ruling E15-8 as A2, A3 and A4 read it;
contract section 5).

Every reviewer workspace and every packet, the local lenses' and the outside rows', the first send and
every retry alike, is built here and only here, from the reviewed commit's objects (the commit `gate.json`
records): never from the working tree, never from an earlier copy. `Snapshot` reads that commit once:
its tree through `git ls-tree`, its stored bytes through `git cat-file --batch` (no attribute, filter or
line-ending rule applies, C1A-5), the build doc's spec (`spec.py`) and the inspection sheet (`sheet.py`).
`build` decides one packet's whole content in memory; `cut` writes it into a fresh directory that must
not exist yet; `check` holds a directory to the content `build` decided, file by file (path, size,
sha256), and is run immediately before a request file is written; `digest` is the content's fingerprint,
recorded by `scope` and required of every later cut.

THE ALLOW RULE (stated once here and once in the contract, section 5). A path reaches a reviewer's
workspace when, and only when, it is a blob of the reviewed commit's tree (a file, an executable, or a
symbolic link written as a plain file holding its target text) and `left_out_by_rule` names no reason to
leave it out:

1. it is not a plain relative path (an empty, `.` or `..` component);
2. two consecutive components of it read `docs` then `reviews` (a prior verdict) or `docs` then
   `records` (the records log), compared without regard to case, wherever in the path they stand;
3. any one of its components, lower-cased with `-`, `_`, `.` and spaces removed, holds `buildernotes` or
   `buildnotes` (the builder's notes: a file or a folder of them, B4);
4. it is `REVIEW.md` at the root (the inspection sheet: never in a workspace; a local lens receives the
   commit's bytes as a document when it is the kit sheet, and no outside packet ever carries it).

The build doc's file in a workspace holds the spec. A commit entry that is not a blob (a submodule) is
not a file and is not copied. A local packet holds the workspace, `documents/spec.md`, the sheet as
`documents/REVIEW.md` when the commit's `REVIEW.md` is the kit sheet, and its lens's mandate; an outside
row that reads a workspace (`repo`) holds the workspace and the outside mandate; a packet-only row holds
the workspace's UTF-8 files staged under `documents/` with every `/` written `__` (C1A-6's naming) and
the outside mandate. Everything left out is named in the packet's withheld list with its reason, and
nothing is named there that the packet holds: every path the rule left out, every submodule, every
section and `Status:` label `spec.py` removed, every untracked, ignored or changed working-tree path (the
names `scope` recorded; their contents are never read), and per packet the sheet where it is not
delivered and, for a packet-only row, each file that is not UTF-8 text.
"""
import hashlib
import json
import os
import re

from station_core import driver, fsio, validate

from . import gitio, sheet as sheetmod, spec as specmod

SHEET = "REVIEW.md"
RECORD_FOLDERS = (("docs", "reviews", "a prior verdict (docs/reviews/)"),
                  ("docs", "records", "the records log (docs/records/)"))
NOTES = re.compile(r"build(?:er)?notes")
SEPARATORS = re.compile(r"[-_. ]")
NOTES_WHY = "the builder's notes"
SHEET_WHY = "the repo's inspection sheet: the local lenses only (its checks are distilled from prior verdicts)"
LISTS = ("files.json", "withheld.json")
SLOTS = ("[BUILD_DOC]", "[BASE_COMMIT]", "[BOUNDARY_FILES]")
REGULAR = ("100644", "100755")


class PacketError(RuntimeError):
    """A packet that cannot be cut where it was asked to be."""


def left_out_by_rule(path):
    """The allow rule: the reason a tracked path never reaches a reviewer's workspace, or None."""
    parts = path.split("/")
    if not path or path.startswith("/") or any(part in ("", ".", "..") for part in parts):
        return "not a plain relative path"
    low = [part.lower() for part in parts]
    for index in range(len(low) - 1):
        for first, second, why in RECORD_FOLDERS:
            if low[index] == first and low[index + 1] == second:
                return why
    for part in low:
        if NOTES.search(SEPARATORS.sub("", part)):
            return NOTES_WHY
    if path == SHEET:
        return SHEET_WHY
    return None


def staged_names(rels):
    """{path: staged name} for a packet-only row, deterministic (C1A-6): every `/` is written `__`; when two
    paths stage to one name, the first in path order keeps it and each later one takes the name with `.2`,
    `.3` and on before its extension, skipping any name another path stages to. No name is given twice."""
    rels = sorted(rels)
    natural = dict((rel, rel.replace("/", "__")) for rel in rels)
    reserved = set(natural.values())
    used, out = set(), {}
    for rel in rels:
        name = natural[rel]
        if name in used:
            stem, ext = os.path.splitext(name)
            number = 2
            while True:
                name = "%s.%d%s" % (stem, number, ext)
                if name not in reserved and name not in used:
                    break
                number += 1
        used.add(name)
        out[rel] = name
    return out


class Snapshot(object):
    """The reviewed commit, read once: `tree` {path: bytes} is the workspace every packet copies (the allow
    rule applied, the build doc's file holding the spec), `modes` {path: git mode}, `left` the tracked
    entries the rule left out, `spec` and `removed` (`spec.py`), `sheet` (`sheet.py`) with `sheet_bytes`,
    `texts` the UTF-8 files of the tree, `binary` the others, `staged` {path: staged name}."""

    def __init__(self, workspace, commit, doc):
        self.workspace, self.commit, self.doc = workspace, commit, doc
        kept, self.left = [], []
        doc_entry = sheet_entry = None
        for mode, kind, oid, path in gitio.tree_entries(workspace, commit):
            if kind != "blob":
                self.left.append({"what": path, "why": "a %s entry (a submodule): not a file, nothing copied" % kind})
                continue
            if path == doc:
                doc_entry = (mode, oid)
            if path == SHEET:
                sheet_entry = (mode, oid)
            why = left_out_by_rule(path)
            if why is not None:
                if path != SHEET:
                    self.left.append({"what": path, "why": why})
                continue
            kept.append((mode, oid, path))
        if doc_entry is None:
            raise driver.Usage("the build doc %s is not a file of the reviewed commit %s: the spec is read from that "
                               "commit only; commit the build doc and run again" % (doc, commit))
        contents = gitio.blobs(workspace, [oid for mode, oid, path in kept] + [doc_entry[1]]
                               + ([sheet_entry[1]] if sheet_entry else []))
        try:
            doc_text = contents[doc_entry[1]].decode("utf-8")
        except UnicodeDecodeError:
            raise driver.Usage("the build doc %s in the reviewed commit is not UTF-8 text" % doc)
        self.spec, self.removed = specmod.clean(doc_text)
        self.tree, self.modes = {}, {}
        for mode, oid, path in kept:
            self.tree[path] = self.spec.encode("utf-8") if path == doc else contents[oid]
            self.modes[path] = mode
        self.sheet_bytes = None
        self.sheet_entry = "absent"
        if sheet_entry is not None and sheet_entry[0] in REGULAR:
            self.sheet_bytes = contents[sheet_entry[1]]
            self.sheet_entry = "regular"
            self.sheet = sheetmod.parse(self.sheet_bytes.decode("utf-8", "replace"))
        else:
            if sheet_entry is not None:
                self.sheet_entry = "not regular"
            self.sheet = sheetmod.absent()
        self.texts, self.binary = {}, []
        for path, data in sorted(self.tree.items()):
            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                self.binary.append(path)
                continue
            self.texts[path] = data
        self.staged = staged_names(self.texts)


def worktree_names(workspace):
    """The working tree's names a packet leaves out, read once by `scope` (names only, never contents):
    {"untracked", "ignored", "changed"}; a changed path is a tracked one the tree holds differently."""
    untracked = gitio.untracked(workspace)
    ignored = gitio.ignored(workspace)
    changed = sorted(p for p in gitio.dirt(workspace) if p not in set(untracked) and not p.endswith("/"))
    return {"untracked": untracked, "ignored": ignored, "changed": changed}


# ---- the mandates ------------------------------------------------------------------------------

def boundary_lines(boundary):
    out = []
    for row in boundary:
        if row.get("from"):
            out.append("%s\t%s -> %s" % (row["status"], row["from"], row["path"]))
        else:
            out.append("%s\t%s" % (row["status"], row["path"]))
    return "\n".join(out)


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


def local_mandate(skill_root, lens, gate, sheet, profile="repo-with-tools"):
    """One local lens's mandate. Its words follow the route (C1A-9): under `repo-with-tools` the lens may
    run the project's tests in its copy; under `repo` it reads and runs nothing, and the mandate says so
    and promises no test run."""
    runs = profile == "repo-with-tools"
    lines = ["# Vertical review: one local lens", "",
             "lens: %s" % lens, "",
             lens_brief(skill_root, lens), ""]
    if not runs:
        lines += ["On this route a lens runs nothing: where this brief says to run something, read the code "
                  "instead and report that check as not executed.", ""]
    lines += ["## The scope", "",
              "The whole vertical: every slice of the build doc, reviewed together against its base.",
              "Base commit: %s" % gate["base"]["commit"], "Head commit: %s" % gate["head"], "",
              "Files this build touched (git diff --name-status <base>..HEAD):", "",
              boundary_lines(gate["boundary"]), "",
              "## What you have", "",
              ("- The workspace: a copy of the reviewed head, its tracked files only, with no history. You may run "
               "the project's tests there; write only to scratch and ignored caches, never a tracked file, and report "
               "\"verification blocked\" for a check the sandbox stopped." if runs else
               "- The workspace: a copy of the reviewed head, its tracked files only, with no history. This route runs "
               "no command: read the code, and report a check you would have run as not executed."),
              "- spec.md: the build doc as the spec. It is the only source of requirements; its ledger (the review "
              "record, the handoff notes and the slices' status lines) and the builder's working records (build "
              "assumptions, deviations, discovered) are left out on purpose, so grade the code against the spec and "
              "never against what an earlier review or the builder concluded."]
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
              "", ("End with what you tried to break and could not, each with how (executed, read or reasoned) and, "
                   "for an executed check, what it printed." if runs else
                   "End with what you tried to break and could not, each with how (read or reasoned).")
              + " A review with no findings is a claim that you tried; make it only after trying."]
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


# ---- one packet --------------------------------------------------------------------------------

def plan(ask, lenses, outside_rows):
    """The packets a run's scope holds: one per local lens, one per outside row the answer named (a named
    row suggest dropped included; it is never sent). Each is {"name", "side", "lens", "row", "profile"}."""
    local = [r for r in ask["rows"] if r["side"] == "local"][0]
    out = [{"name": "local-%s" % lens, "side": "local", "lens": lens, "row": None, "profile": local["profile"]}
           for lens in lenses]
    rows = dict((r["row"], r) for r in ask["rows"])
    for row in ask["answer"]["rows"]:
        if row in outside_rows and row in rows:
            out.append({"name": "outside-%s" % row, "side": "outside", "lens": None, "row": row,
                        "profile": rows[row]["profile"]})
    return out


def _withheld(snap, spec, worktree):
    local = spec["side"] == "local"
    out = list(snap.left)
    if snap.sheet_entry != "absent":
        if snap.sheet_entry == "not regular":
            out.append({"what": SHEET, "why": "not a regular file in the reviewed commit (a link or another kind): no "
                                              "sheet, the defaults apply, and no lens receives it"})
        elif not local:
            out.append({"what": SHEET, "why": SHEET_WHY})
        elif snap.sheet["state"] != "read":
            out.append({"what": SHEET, "why": "present in the reviewed commit but not the kit sheet: the defaults "
                                              "apply, and no lens receives it"})
    for item in snap.removed:
        label = item["what"] if item["what"] != "Status: line" else "Status: line %d" % item["lines"][0]
        kind = "ledger" if item["what"] in specmod.LEDGER + ("Status: line",) else "working record"
        out.append({"what": "%s %s" % (snap.doc, label),
                    "why": "the build doc's %s, lines %d to %d (E15-8)" % ((kind,) + tuple(item["lines"]))})
    out += [{"what": p, "why": "untracked: not in the reviewed commit"} for p in worktree.get("untracked") or []]
    out += [{"what": p, "why": "ignored: not in the reviewed commit"} for p in worktree.get("ignored") or []]
    out += [{"what": p, "why": "a working-tree change: the copy holds the reviewed commit's bytes"}
            for p in worktree.get("changed") or []]
    if spec["side"] == "outside" and spec["profile"] != "repo":
        out += [{"what": p, "why": "not UTF-8 text: a packet-only reviewer receives text files only"}
                for p in snap.binary]
    return out


def build(snap, spec, gate, skill_root, worktree):
    """One packet's whole content, decided in memory from the snapshot: {"files": {at: bytes}, "meta": {at:
    {"role", "path", "source"}}, "modes", "workspace", "documents", "mandate", "withheld", "left_out"} plus the
    packet's own fields. `at` is the path inside the packet's directory."""
    files, meta, modes = {}, {}, {}
    workspace = spec["side"] == "local" or spec["profile"] == "repo"
    if workspace:
        for path, data in snap.tree.items():
            at = "workspace/" + path
            files[at] = data
            meta[at] = {"role": "workspace", "path": path}
            modes[at] = snap.modes[path]
    documents, left_out = [], []
    if spec["side"] == "local":
        files["documents/spec.md"] = snap.spec.encode("utf-8")
        meta["documents/spec.md"] = {"role": "document", "path": "spec.md"}
        documents.append("documents/spec.md")
        if snap.sheet["state"] == "read":
            files["documents/REVIEW.md"] = snap.sheet_bytes
            meta["documents/REVIEW.md"] = {"role": "document", "path": SHEET}
            documents.append("documents/REVIEW.md")
        mandate = local_mandate(skill_root, spec["lens"], gate, snap.sheet, spec["profile"])
    else:
        if not workspace:
            for path, name in sorted(snap.staged.items(), key=lambda pair: pair[1]):
                at = "documents/" + name
                files[at] = snap.texts[path]
                meta[at] = {"role": "document", "path": name, "source": path}
                documents.append(at)
            left_out = list(snap.binary)
        mandate = outside_mandate(skill_root, snap.spec, gate)
    files["mandate.md"] = mandate.encode("utf-8")
    meta["mandate.md"] = {"role": "mandate", "path": "mandate.md"}
    out = dict((k, spec.get(k)) for k in ("name", "side", "lens", "row", "profile"))
    out.update(commit=snap.commit, files=files, meta=meta, modes=modes, workspace=workspace, documents=documents,
               mandate="mandate.md", withheld=_withheld(snap, spec, worktree), left_out=left_out)
    return out


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest(built):
    """[{"at", "path", "role", "size", "sha256"} (and "source" for a staged file)], in `at` order."""
    out = []
    for at in sorted(built["files"]):
        data = built["files"][at]
        entry = dict(built["meta"][at], at=at, size=len(data), sha256=_sha(data))
        out.append(entry)
    return out


def digest(built):
    """The content's fingerprint: its manifest, its withheld list and its left-out list."""
    body = {"manifest": manifest(built), "withheld": built["withheld"], "left_out": built["left_out"]}
    return _sha(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def cut(built, dest):
    """Write the packet into `dest`, a directory that must not exist yet, and its two lists beside the
    material (`files.json`, `withheld.json`, never handed to a reviewer). Returns the absolute paths a
    request names: {"dir", "workspace", "documents", "mandate", "files", "withheld"}."""
    if os.path.lexists(dest):
        raise PacketError("the packet's directory already exists, and a packet is always cut fresh: %s" % dest)
    os.makedirs(dest)
    for at in sorted(built["files"]):
        target = os.path.join(dest, *at.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "xb") as fh:
            fh.write(built["files"][at])
        os.chmod(target, 0o755 if built["modes"].get(at) == "100755" else 0o644)
    entries = [dict(e, abs=os.path.join(dest, *e["at"].split("/"))) for e in manifest(built)]
    workspace = os.path.join(dest, "workspace") if built["workspace"] else None
    fsio.write_json(os.path.join(dest, "files.json"), {"packet": built["name"], "side": built["side"],
                                                       "lens": built["lens"], "row": built["row"],
                                                       "profile": built["profile"], "commit": built["commit"],
                                                       "workspace": workspace, "files": entries})
    fsio.write_json(os.path.join(dest, "withheld.json"), {"packet": built["name"], "withheld": built["withheld"],
                                                          "left_out": built["left_out"]})
    return {"dir": dest, "workspace": workspace,
            "documents": [os.path.join(dest, *at.split("/")) for at in built["documents"]],
            "mandate": os.path.join(dest, built["mandate"]), "files": os.path.join(dest, "files.json"),
            "withheld": os.path.join(dest, "withheld.json")}


def check(built, dest):
    """[problem] for every way the directory differs from the content `build` decided (a file added, changed
    or gone, a link, a special file); [] when it holds byte for byte."""
    expected = dict((at, (len(data), _sha(data))) for at, data in built["files"].items())
    problems, seen = [], set()
    if not os.path.isdir(dest) or os.path.islink(dest):
        return ["the packet's directory %s is not there" % dest]
    for base, dirs, names in os.walk(dest):
        for name in sorted(dirs):
            if os.path.islink(os.path.join(base, name)):
                problems.append("%s is a link" % os.path.relpath(os.path.join(base, name), dest).replace(os.sep, "/"))
        for name in sorted(names):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, dest).replace(os.sep, "/")
            if rel in LISTS:
                continue
            if os.path.islink(full) or not os.path.isfile(full):
                problems.append("%s is not a regular file" % rel)
                continue
            if rel not in expected:
                problems.append("%s was added after the packet was cut" % rel)
                continue
            seen.add(rel)
            if (os.path.getsize(full), fsio.sha256_file(full)) != expected[rel]:
                problems.append("%s changed after the packet was cut" % rel)
    problems += ["%s is gone" % at for at in sorted(set(expected) - seen)]
    return problems
