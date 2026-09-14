"""The checkpoint (pilot contract section 11): write with integrity and log-before-rename,
read with the chain check and the one tolerated state (E8-15), the binding hash (E8-9), the
item-state union, the artifact ledger (E8-29), run_date and session_wrote_fix (E8-13, E8-25).

Every write validates the document against checkpoint.schema.json first; a write that would
not validate raises (a core defect, exit 1), never lands.
"""
import json
import os

from . import canon, validate

FILE = "checkpoint.json"
LOG = "checkpoint.log"
ARTIFACT_ORDER_FIRST = ("input.json", "resolved-input.json", "checklist.md", "checklist.json", "checkpoint.json", "checkpoint.log")
ARTIFACT_ORDER_LAST = ("receipt.json", "receipt.log")
NOT_ARTIFACTS = ("result.json", "chat.md", "result.invalid.json", "result.invalid.validation.json")


class CheckpointError(RuntimeError):
    pass


def serialize(doc):
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def self_hash(doc):
    body = dict(doc)
    integ = dict(doc.get("integrity") or {})
    integ.pop("self", None)
    body["integrity"] = integ
    return canon.sha256_hex(canon.canonical_json(body))


def read_log(path):
    """[(seq, hash)] or raises CheckpointError on a malformed line."""
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for n, line in enumerate(fh.read().splitlines(), 1):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) != 64:
                raise CheckpointError("%s line %d is not `<seq> <sha256>`: %r" % (os.path.basename(path), n, line))
            rows.append((int(parts[0]), parts[1]))
    return rows


def verify_integrity(doc, log_rows, name="checkpoint"):
    """Section 11 integrity against the log. Returns {"ok", "tolerated", "reason"}."""
    integ = doc.get("integrity") or {}
    seq, prev, self_ = integ.get("seq"), integ.get("prev"), integ.get("self")
    if self_hash(doc) != self_:
        return {"ok": False, "tolerated": False, "reason": "%s integrity.self does not recompute" % name}
    seqs = [r[0] for r in log_rows]
    if seqs != list(range(len(seqs))):
        return {"ok": False, "tolerated": False, "reason": "%s.log has a gap or a repeated seq (%s)" % (name, ", ".join(str(s) for s in seqs))}
    if not log_rows:
        return {"ok": False, "tolerated": False, "reason": "%s.log is empty" % name}

    def prev_ok(idx):
        if seq == 0:
            return prev is None and idx == 0
        return idx >= 1 and prev == log_rows[idx - 1][1]

    last = log_rows[-1]
    if last == (seq, self_):
        if prev_ok(len(log_rows) - 1):
            return {"ok": True, "tolerated": False, "reason": ""}
        return {"ok": False, "tolerated": False, "reason": "%s integrity.prev is not the log line before its own" % name}
    if len(log_rows) >= 2 and log_rows[-2] == (seq, self_) and last[0] == seq + 1:
        if prev_ok(len(log_rows) - 2):
            return {"ok": True, "tolerated": True, "reason": "%s.log announces seq %d that never landed; dropped (section 11)" % (name, last[0])}
        return {"ok": False, "tolerated": False, "reason": "%s.log announces seq %d beside a corrupted earlier line: integrity.prev is not the line before the checkpoint's own (E8-15)" % (name, last[0])}
    if seq > last[0]:
        return {"ok": False, "tolerated": False, "reason": "%s is ahead of its log (seq %d, log ends at %d)" % (name, seq, last[0])}
    return {"ok": False, "tolerated": False, "reason": "%s (seq %d, self %s...) is not the log's last line" % (name, seq, (self_ or "")[:12])}


def drop_last_log_line(path):
    rows = read_log(path)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for seq, h in rows[:-1]:
            fh.write("%d %s\n" % (seq, h))


class Checkpoint:
    """A checkpoint document with its chain state; save() appends one write."""

    def __init__(self, run_dir, doc, schemas):
        self.run_dir = run_dir
        self.doc = doc
        self.schemas = schemas

    @property
    def path(self):
        return os.path.join(self.run_dir, FILE)

    @property
    def log_path(self):
        return os.path.join(self.run_dir, LOG)

    @classmethod
    def new(cls, run_dir, doc, schemas):
        doc = dict(doc)
        doc["integrity"] = {"seq": 0, "prev": None, "self": "0" * 64}
        cp = cls(run_dir, doc, schemas)
        cp._write(0, None)
        return cp

    def save(self):
        integ = self.doc["integrity"]
        self._write(integ["seq"] + 1, integ["self"])

    def _write(self, seq, prev):
        self.doc["integrity"] = {"seq": seq, "prev": prev, "self": "0" * 64}
        self.doc["integrity"]["self"] = self_hash(self.doc)
        errors = validate.validate_checkpoint(self.doc, self.schemas)
        if errors:
            raise CheckpointError("checkpoint would not validate: %s %s" % (errors[0]["path"], errors[0]["message"]))
        canon.log_then_rename(self.log_path, "%d %s" % (seq, self.doc["integrity"]["self"]), self.path, serialize(self.doc))

    def add_artifact(self, path):
        arts = self.doc.setdefault("artifacts", [])
        if path not in arts:
            arts.append(path)


def read_and_verify(run_dir, schemas):
    """Section 11 steps 1 and 2. Returns {"ok", "step", "reason", "doc", "tolerated"}."""
    path, log = os.path.join(run_dir, FILE), os.path.join(run_dir, LOG)
    if not os.path.isfile(path):
        return {"ok": False, "step": 1, "reason": "checkpoint.json does not exist in %s" % run_dir, "doc": None, "tolerated": False}
    if not os.path.isfile(log):
        return {"ok": False, "step": 1, "reason": "checkpoint.log does not exist in %s" % run_dir, "doc": None, "tolerated": False}
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        return {"ok": False, "step": 1, "reason": "checkpoint.json does not parse: %s" % exc, "doc": None, "tolerated": False}
    try:
        rows = read_log(log)
    except CheckpointError as exc:
        return {"ok": False, "step": 1, "reason": str(exc), "doc": doc, "tolerated": False}
    errors = validate.validate_checkpoint(doc, schemas)
    if errors:
        return {"ok": False, "step": 1, "reason": "checkpoint fails its schema at %s: %s" % (errors[0]["path"], errors[0]["message"]), "doc": doc, "tolerated": False}
    v = verify_integrity(doc, rows, "checkpoint")
    if not v["ok"]:
        return {"ok": False, "step": 2, "reason": v["reason"], "doc": doc, "tolerated": False}
    return {"ok": True, "step": 2, "reason": v["reason"], "doc": doc, "tolerated": v["tolerated"]}


def load(run_dir, schemas):
    """A verified checkpoint as a Checkpoint object, or raises CheckpointError."""
    v = read_and_verify(run_dir, schemas)
    if not v["ok"]:
        raise CheckpointError("step %d: %s" % (v["step"], v["reason"]))
    return Checkpoint(run_dir, v["doc"], schemas), v


def pending(doc):
    return [i for i, it in enumerate(doc["items"]) if it["state"] == "pending"]


def done_results(doc):
    return [(i, it["result"]) for i, it in enumerate(doc["items"]) if it["state"] == "done"]


def scan_artifacts(run_dir):
    """E8-29: the run directory in canonical order for a checkpoint without an artifact ledger."""
    found = []
    for root, dirs, files in os.walk(run_dir):
        dirs.sort()
        for name in sorted(files):
            rel = os.path.relpath(os.path.join(root, name), run_dir)
            if rel in NOT_ARTIFACTS or name.startswith("."):
                continue
            found.append(rel)
    first = [n for n in ARTIFACT_ORDER_FIRST if n in found]
    verifier = sorted(n for n in found if n.startswith("verifier" + os.sep) or n.startswith("verifier/"))
    last = [n for n in ARTIFACT_ORDER_LAST if n in found]
    rest = sorted(n for n in found if n not in first and n not in verifier and n not in last)
    return [os.path.join(run_dir, n) for n in first + verifier + last + rest]


def artifacts(doc, run_dir):
    if doc.get("artifacts") is not None:
        return list(doc["artifacts"])
    return scan_artifacts(run_dir)
