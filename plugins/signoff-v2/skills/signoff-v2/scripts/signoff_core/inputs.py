"""Loading and resolving the one validated input structure, and the run's state between phases.

The input is validated once, at `check-input`, and the resolved copy is written to the run
directory as `input.json`. Every later phase reads that copy and the run's `state.json` rather
than the caller's file, so a phase cannot be handed a different input halfway through a run.

`state.json` is this station's checkpoint. It carries what one phase computed and the next needs,
and one thing that is load-bearing: `records_pin`, the document, its log and the HEAD the run
read its state against (Revision 7). At `record`, before this run's own levelling, the log must
still be at that head.
"""
import datetime
import json
import os

from . import canon


class InputError(RuntimeError):
    """The input could not be loaded at all: not there, not JSON."""


def load(path):
    if not os.path.isfile(path):
        raise InputError("the input file %s does not exist" % path)
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except ValueError as failure:
        raise InputError("the input file %s is not JSON: %s" % (path, failure))
    except (OSError, UnicodeDecodeError) as failure:
        raise InputError("the input file %s could not be read: %s" % (path, failure))


def load_schema(references, name):
    with open(os.path.join(references, name), "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def today():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")


def resolve(doc):
    """The input with its defaults filled in. Never changes a value the caller supplied."""
    out = json.loads(json.dumps(doc))
    invocation = out.setdefault("invocation", {})
    invocation.setdefault("run_date", today())
    invocation.setdefault("harness", None)
    invocation.setdefault("model", None)
    out.setdefault("report_only", False)
    review = out.setdefault("review", {})
    review.setdefault("depth", "LEAN")
    review.setdefault("lenses", lenses_for(review["depth"]))
    review.setdefault("route", None)
    review.setdefault("builder_conversation", [])
    return out


def lenses_for(depth):
    """v1 Step 3's sets. LIGHT is one fused reviewer; DEEP adds security and tests."""
    if depth == "LIGHT":
        return ["spec+correctness"]
    if depth == "DEEP":
        return ["spec", "correctness", "seams", "security", "tests"]
    return ["spec", "correctness", "seams"]


def at_instant(run_date):
    """The `at` every event of this run carries: the run date, as an RFC 3339 UTC instant.

    The block heading carries the run date (Appendix A), so every event of the run carries that
    date. A fixed time of day keeps two runs of one case byte-comparable."""
    return "%sT00:00:00Z" % run_date


class Run:
    """The run directory: the resolved input, the state between phases, and the result."""

    def __init__(self, run_dir):
        self.run_dir = run_dir
        self.input_path = os.path.join(run_dir, "input.json")
        self.state_path = os.path.join(run_dir, "state.json")
        self.result_path = os.path.join(run_dir, "result.json")
        self.written = []

    # ---- artifacts -----------------------------------------------------------------------

    def ensure(self):
        if not os.path.isdir(self.run_dir):
            os.makedirs(self.run_dir)
        return self.run_dir

    def note_write(self, path, kind):
        row = {"path": path, "kind": kind}
        if row not in self.written:
            self.written.append(row)
        return row

    def save_input(self, doc):
        self.ensure()
        canon.write_json(self.input_path, doc)
        self.note_write(self.input_path, "run_artifact")
        return self.input_path

    def load_input(self):
        return canon.read_json(self.input_path)

    def save_state(self, state):
        self.ensure()
        canon.write_json(self.state_path, state)
        self.note_write(self.state_path, "run_artifact")
        return self.state_path

    def load_state(self):
        if not os.path.isfile(self.state_path):
            return None
        return canon.read_json(self.state_path)

    def scratch(self, name):
        path = os.path.join(self.run_dir, name)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    def has_result(self):
        return os.path.isfile(self.result_path)

    def save_result(self, result):
        self.ensure()
        canon.write_json(self.result_path, result)
        self.note_write(self.result_path, "run_artifact")
        return self.result_path
