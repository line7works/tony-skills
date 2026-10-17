"""A safe ground disproved (the frame's SEC-12; SEC-1, SEC-4, SEC-9).

Each time a value enters the register, the invocation searches for it in what its run has on record
as safe: the saved inputs, every manifest and the journal. Where they hold it, a safe ground is
disproved. `search` is that search. `owed_for` builds the disproof record owed for a find: it says
where the value rests in the run directory and holds nothing of the value.

`startup_read` is the disproof read, the last of the startup checks: it reads every disproof record
of the run's journal back into the register, then makes the search for three more kinds of value
(the secrets the register already holds; each secret the manifest shows the run reads from a file
on this machine; the value of a receipt that is due and not given, where its protected record is
present). It writes nothing. What it finds is returned as the records owed, to be written first
once the startup checks have passed, in the one order `first_records` gives (H13).
"""
import json
import os

from . import channels, disproofs, journal as journalmod, protected, rundir

MOST_SPANS = 32


def record_files(fs, run_dir):
    """The files that hold what the run has on record as safe, in a fixed order."""
    try:
        listing = fs.listdir(run_dir)
    except OSError:
        listing = []
    # the saved inputs: the first look's and every re-plan's, one a planning stop ended among them (RUN-4, RUN-12)
    names = sorted((n for n in listing if rundir.is_inputs_name(n)),
                   key=lambda n: [0] if n == "inputs.json" else [int(p) for p in n[len("inputs-"):-len(".json")].split("-")])
    names += sorted((n for n in listing if n.startswith("manifest-") and n.endswith(".json")),
                    key=lambda n: int(n[len("manifest-"):-len(".json")] or 0) if n[len("manifest-"):-len(".json")].isdigit() else 0)
    names.append(journalmod.FILE_NAME)
    return [n for n in names if n in listing]


def _needles(entry):
    out = []
    for form in entry.forms:
        for text in (form, json.dumps(form, ensure_ascii=False)[1:-1]):
            raw = text.encode("utf-8")
            if raw and raw not in out:
                out.append(raw)
    return out


def search(fs, run_dir, entry):
    """Every place the run's records hold the entry, in any form: [{file, start, end}], capped."""
    spans = []
    needles = _needles(entry)
    for name in record_files(fs, run_dir):
        try:
            data = fs.read(os.path.join(run_dir, name))
        except OSError:
            continue
        for needle in needles:
            at = data.find(needle)
            while at != -1 and len(spans) < MOST_SPANS:
                span = {"file": name, "start": at, "end": at + len(needle)}
                if span not in spans:
                    spans.append(span)
                at = data.find(needle, at + 1)
    return spans


def owed_for_channel(spans, channel):
    return {"source": "channel", "channel": channel, "rests": {"content": spans[0]}, "found": spans[:MOST_SPANS]}


def owed_for_field(reference, spans, op=None, execution=None):
    record = {"source": "secret field", "rests": {"protected": reference}, "found": spans[:MOST_SPANS]}
    if op is not None:
        record["op"] = op
    if execution is not None:
        record["execution"] = execution
    return record


def receipts_due(records):
    """Every receipt that is due and not given, in journal order and, within one due record, in the declaration's
    order: [{"op", "execution", "command", "field", "record"}]. Each execution answers for itself, and in it each
    secret field for itself (SEC-12), so a receipt is given for one (operation, execution, field) and no other."""
    given = set((r.get("op"), r.get("execution"), r.get("field")) for r in records
                if r.get("kind") == "step" and r.get("step") == "receipt")
    out = []
    for r in records:
        if r.get("kind") != "step" or r.get("step") != "receipt-due":
            continue
        for item in r.get("fields") or []:
            if (r.get("op"), r.get("execution"), item.get("field")) not in given:
                out.append({"op": r.get("op"), "execution": r.get("execution"), "command": r.get("command"),
                            "field": item.get("field"), "record": item.get("record")})
    return out


def _already(found, value):
    return any(value == v or value in comps for _r, v, comps in found)


def startup_read(world, run_dir, journal, register, tokens, secret_reads):
    """The disproof read. Returns (disproof records owed, receipts owed), nothing written.

    `tokens` is {provider: token} as the name check read them; `secret_reads` is what the manifest
    shows the run reads a secret from: [{"file": path, "keys": [names]}]."""
    fs = world.fs
    found, every = disproofs.read_all(fs, run_dir, journal.records)
    if not every:
        raise rundir.Failed("disproof-unreadable")
    for record, value, components in found:
        register.add(value, components, disproofs.reference_of(record), "disproof")
    try:
        register.add(protected.read_key(fs, run_dir), (), None, "fingerprint key")
    except OSError:
        raise rundir.Failed("permissions")
    owed, receipts = [], []
    # one: each secret the register already holds, which is what the name check read
    for provider in sorted(tokens):
        entry = register.add(tokens[provider], (), None, "channel")
        spans = search(fs, run_dir, entry) if entry else []
        if spans and not _already(found, tokens[provider]):
            owed.append(owed_for_channel(spans, "hosting-token"))
    # two: each secret the manifest shows the run reads from a file on this machine
    for item in secret_reads or []:
        address = channels.read_connection(world, item.get("file") or "", item.get("keys") or [])
        if not address:
            continue
        entry = register.add(address, channels.address_components(address), None, "channel")
        spans = search(fs, run_dir, entry) if entry else []
        if spans:
            data = fs.read(os.path.join(run_dir, spans[0]["file"]))[spans[0]["start"]:spans[0]["end"]].decode("utf-8", "replace")
            if not _already(found, data):
                owed.append(owed_for_channel(spans, "connection"))
    # three: a receipt that is due and not given, where its protected record is present
    for due in receipts_due(journal.records):
        record_id = due.get("record")
        if not record_id or not protected.present(fs, run_dir, record_id):
            continue
        try:
            content = fs.read(protected.path_of(run_dir, record_id))
            doc = protected.open_envelope(content)
            key = protected.read_key(fs, run_dir)
        except (OSError, protected.Unreadable):
            raise rundir.Failed("disproof-unreadable")
        reference = {"record": record_id, "type": "secret field",
                     "label": "the secret field %s of %s" % (due.get("field"), due.get("command") or "a command"),
                     "fingerprint": protected.fingerprint(key, content)}
        entry = register.add(doc["raw"], [c for c in doc["components"] if isinstance(c, str)], None, "secret field")
        spans = search(fs, run_dir, entry) if entry else []
        if spans and not _already(found, doc["raw"]):
            owed.append(owed_for_field(reference, spans, due.get("op"), due.get("execution")))
        receipts.append({"op": due.get("op"), "execution": due.get("execution"), "command": due.get("command"),
                         "field": due.get("field"), "record": record_id, "reference": reference})
    return owed, receipts


def write_owed(world, journal, register, owed, receipts):
    """First, each disproof record owed; second, each receipt owed (SEC-12, the order of first
    records). Each disproof record's reference is given to the register entry it withholds."""
    written = []
    for item in owed:
        record = journal.append(world, "disproof", register=register, **item)
        written.append(record)
        value, components = disproofs.read_value(world.fs, journal.run_dir, record)
        register.add(value, components, disproofs.reference_of(record), "disproof")
        for entry in register.entries:
            if entry.value == value and not entry.ref:
                entry.ref = disproofs.reference_of(record)
    for item in receipts:
        fields = {"op": item["op"], "step": "receipt", "execution": item["execution"], "field": item["field"],
                  "outcome": "kept", "reference": item["reference"]}
        if item.get("command"):
            fields["command"] = item["command"]
        written.append(journal.append(world, "step", register=register, **fields))
    return written
