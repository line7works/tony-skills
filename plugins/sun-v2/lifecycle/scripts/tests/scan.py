"""The scan of SEC-11: how the secret rules are tested.

It looks for a marked canary and for every value a fake issued during a run: whole, by each
component, and in the percent-encoded and base64 forms of both (`needles`: percent-encoding plain and
with the form encoding's plus, capital and lower-case escapes; base64 standard and link-safe, with
and without padding). It covers every file under the
fixture home (the working tree is under it), both output streams of every invocation given to it,
every argument and environment that every fake recorded for itself and for anything it started, and
every git object under the home, loose and packed (each object of a pack read whole, its deltas applied, by the tool's own
reader of git's files). Nothing under the home is passed over but the fakes' own provider side. A value found outside a place of SEC-7, or at one with wider
permissions than SEC-7 gives, is a finding.

A fake's own state and its own list of what it issued are the provider's side and the scan's source,
not a place the tool wrote; they are left out. What a fake writes into a log of its own is risk RK1.
"""
import base64
import json
import os
import re
import stat
import struct
import sys
import urllib.parse
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sun_core import gitread, rundir  # noqa: E402

PROVIDER_SIDE = ("state.json", "issued.jsonl", "plan.json", "counts.json", "passfile.jsonl", "own.log", "state.json.new")


def _lower_escapes(text):
    return re.sub(r"%[0-9A-F]{2}", lambda m: m.group(0).lower(), text)


def needles(value, components=()):
    """What the scan looks for, of a value and of each of its components (SEC-11: "whole, for each of its components, and
    for the percent-encoded and base64 forms of both"): each whole; its percent-encoding plain and with the form encoding's
    plus, each with capital and with lower-case escapes; and its base64 in the standard and the link-safe alphabets, each
    with and without its padding (the reviewer's S2; the owner's ruling, A140). The scan's own list, kept apart from the
    tool's `screen.forms_of`, so that the scan does not take the tool's word for what a form is."""
    out = []
    for item in [value] + list(components):
        if not item:
            continue
        raw = item.encode("utf-8")
        plain, plus = urllib.parse.quote(item, safe=""), urllib.parse.quote_plus(item, safe="")
        standard, link_safe = base64.b64encode(raw).decode(), base64.urlsafe_b64encode(raw).decode()
        for form in (item, plain, _lower_escapes(plain), plus, _lower_escapes(plus),
                     standard, standard.rstrip("="), link_safe, link_safe.rstrip("=")):
            if form and form not in out:
                out.append(form)
    return out


def issued(machine):
    out = []
    root = os.path.join(machine.home, ".fakes")
    for tool in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        for entry in machine.fake(tool, "issued.jsonl", []) or []:
            out.append(entry["value"])
    return out


def allowed(machine, path):
    """Whether a path is a place of SEC-7 on the fixture machine, by where it lies. In a run directory SEC-7's places are
    "the protected folder of the run directory", "staging" and "the private password file" (SEC-2), which the build keeps
    at `private/password-<operation>` (`rundir.PASSWORD_PREFIX`): of the `private/` folder that one file is a place, and no
    other file in it or below it."""
    runs = machine.facts.runs_root + os.sep
    if path.startswith(runs):
        rest = path[len(runs):].split(os.sep)
        if len(rest) > 1 and rest[1] in ("protected", "staging"):
            return True
        return len(rest) == 3 and rest[1] == "private" and rest[2].startswith(rundir.PASSWORD_PREFIX)
    return path == machine.facts.keying_file or path in getattr(machine, "secret_places", ())


def object_store(home, parts):
    """The git folder whose object store holds the file at `parts` (from the home), or None: a folder named `objects` whose
    parent holds git's `HEAD`, a bare repository's included."""
    for i in range(len(parts) - 1, 0, -1):
        if parts[i] == "objects":
            gitdir = os.path.join(home, *parts[:i])
            if os.path.isfile(os.path.join(gitdir, "HEAD")):
                return gitdir
    return None


def packed(gitdir, pack_path):
    """[(id, body)] of every object of one pack, read whole by the tool's own reader of git's files."""
    stem = pack_path[:-len(".pack")]
    if not os.path.isfile(stem + ".idx"):
        return []
    repo = gitread.Repository(gitdir, gitdir)
    pack = gitread.Pack(stem)
    names = 8 + 256 * 4
    out = []
    for i in range(pack.count):
        sha = pack.idx[names + i * 20:names + i * 20 + 20].hex()
        try:
            out.append((sha, pack.object_at(pack.offset_of(sha), repo)[1]))
        except (gitread.Unreadable, struct.error, zlib.error, IndexError) as exc:
            out.append((sha, ("an object the scan could not read: %s" % type(exc).__name__).encode()))
    return out


def scan(machine, values, results=()):
    """[(where, what)] for every value found where it may not rest. `values` is [(value, components)]."""
    wanted = []
    for value, components in values:
        for form in needles(value, components):
            wanted.append((form, value))
    findings = []

    def look(where, text, path=None):
        for form, value in wanted:
            if form in text:
                if path is not None and path in getattr(machine, "owner_files", ()):
                    continue          # the owner's own file, where his own content was before the run and stays
                if path is not None and allowed(machine, path):
                    mode = stat.S_IMODE(os.lstat(path).st_mode)
                    if mode & 0o077:
                        findings.append((where, "at a place of SEC-7 with wider permissions"))
                    continue
                findings.append((where, "a value in the form %r" % (form[:12] + "...")))
                return
    for base, dirs, files in os.walk(machine.home, followlinks=False):
        for name in files:
            path = os.path.join(base, name)
            rel = os.path.relpath(path, machine.home)
            parts = rel.split(os.sep)
            if parts[0] == ".fakes" and name in PROVIDER_SIDE:
                continue
            try:
                data = open(path, "rb").read()
            except OSError:
                continue
            store = object_store(machine.home, parts)
            if store and parts[-2] != "pack":
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    pass
            if store and parts[-2] == "pack" and name.endswith(".pack"):
                for sha, body in packed(store, path):
                    look("%s (object %s)" % (rel, sha), body.decode("utf-8", "replace"))
            look(rel, data.decode("utf-8", "replace"), path)
            look(rel + " (its name)", name)
    for index, result in enumerate(results):
        look("standard output of invocation %d" % index, result.out)
        look("standard error of invocation %d" % index, result.err)
    return findings
