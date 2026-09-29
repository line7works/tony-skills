"""The run's receipt (CR-13): every write the run makes, with the bytes' hash before and after.

`<run_dir>/receipt.json` is `{"receipt_version": 1, "writes": [{"path", "kind", "sha256_before",
"sha256_after"}, ...]}` in the order the writes happened. A document is written through a
temporary file in its own folder and a rename (`station_core/fsio.atomic_write`); before the
rename the bytes on disk are compared with what the run expects there, and a difference writes
nothing (`Changed`). `report` copies the receipt into the result's `writes`.
"""
import os

from station_core import fsio

NAME = "receipt.json"


class Changed(RuntimeError):
    """The bytes at a path are not the bytes the run expected there; nothing was written."""

    def __init__(self, path, expected, found):
        RuntimeError.__init__(self, "%s changed on disk: the run expected %s and found %s; nothing was "
                              "written" % (path, expected or "no file", found or "no file"))
        self.path, self.expected, self.found = path, expected, found


class Receipt(object):

    def __init__(self, run_dir):
        self.run_dir = run_dir
        self.path = os.path.join(run_dir, NAME)
        self.writes = []
        if os.path.isfile(self.path):
            self.writes = list(fsio.read_json(self.path).get("writes") or [])

    def last_after(self, path):
        """The hash this run last wrote at `path`, or False when the run never wrote it."""
        for row in reversed(self.writes):
            if row["path"] == path:
                return row["sha256_after"]
        return False

    def save(self):
        fsio.write_json(self.path, {"receipt_version": 1, "writes": self.writes})

    def kind_for(self, path):
        return "run_artifact" if fsio.inside(path, self.run_dir) else "document"

    def write(self, path, data, expect=False):
        """Write `data` (text or bytes) to `path` atomically and record it. `expect` is the hash the
        bytes on disk must have first (None: no file); False skips the comparison."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        before = fsio.sha256_file_or_none(path)
        if expect is not False and before != expect:
            raise Changed(path, expect, before)
        fsio.atomic_write(path, data)
        row = {"path": path, "kind": self.kind_for(path), "sha256_before": before,
               "sha256_after": fsio.sha256_bytes(data)}
        self.writes.append(row)
        self.save()
        return row

    def write_json(self, path, doc):
        return self.write(path, fsio.dumps(doc))
