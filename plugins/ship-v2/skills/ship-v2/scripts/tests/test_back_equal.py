"""The back frame is a copy, not a fork (ruling E15-3; the E15 lane contract section 7).

`references/back-files.txt` (itself a back-frame file) lists every file the three back cores
(`vertical-v2`, `handoff-v2`, `ship-v2`) hold identical, relative to the plugin root, `{core}` standing
for the core's own name, each with the source of its bytes in brackets:

    [precon-v2]            copied byte for byte from precon-v2's canonical copy
    [vertical-v2]          new in E15; vertical-v2 holds the canonical copy
    [..., seeded]          carried once the core holds a seeded-case family

Each listed file is compared with its source's copy, found through the checkout layout (this plugin
root's parent, `plugins/`). In the installed shape no such sibling is there, and the comparison is
reported as SKIPPED with that reason, never as passed. `BACK_EQUAL_ROOT` points the check at another
copy of a back core's plugin folder (the one-byte proof uses it), with `BACK_EQUAL_SIBLINGS` naming the
folder that holds the canonical cores.
"""
import hashlib
import os
import re
import unittest

import testlib

BACK_CORES = ("vertical-v2", "handoff-v2", "ship-v2")
SOURCES = ("precon-v2", "vertical-v2")
ROW = re.compile(r"^(?P<path>\S+)  \[(?P<source>[a-z0-9-]+)(?P<seeded>, seeded)?\]$")
FAMILY = re.compile(r"^[A-Z][0-9]+-")


def plugin_root():
    return os.environ.get("BACK_EQUAL_ROOT") or testlib.PLUGIN


def core_of(root):
    """The core's name: its manifest's, else its folder's (an installed copy sits under its version)."""
    import json
    try:
        with open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            name = json.load(fh).get("name")
        if isinstance(name, str) and name:
            return name
    except (OSError, ValueError):
        pass
    return os.path.basename(os.path.normpath(root))


def siblings_dir(root):
    return os.environ.get("BACK_EQUAL_SIBLINGS") or os.path.dirname(os.path.normpath(root))


def list_path(root):
    return os.path.join(root, "skills", core_of(root), "references", "back-files.txt")


def listed(root):
    """[(path, source, seeded)] in file order; a malformed row raises ValueError naming it."""
    rows = []
    with open(list_path(root), encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            match = ROW.match(line)
            if not match or match.group("source") not in SOURCES:
                raise ValueError("back-files.txt line %d is not '<path>  [<source>[, seeded]]': %r" % (number, line))
            rows.append((match.group("path"), match.group("source"), bool(match.group("seeded"))))
    return rows


def has_family(root):
    seeded = os.path.join(root, "evals", "seeded-cases")
    return os.path.isdir(seeded) and any(FAMILY.match(n) and os.path.isdir(os.path.join(seeded, n))
                                         for n in os.listdir(seeded))


def carried(root):
    """The rows this core must hold: every row, and the seeded rows only when it holds a family."""
    family = has_family(root)
    return [(p, s, seeded) for p, s, seeded in listed(root) if family or not seeded]


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def canonical(name, root):
    """The canonical core's plugin folder beside `root`, or None (the installed shape)."""
    if name == core_of(root):
        return root
    path = os.path.join(siblings_dir(root), name)
    return path if os.path.isfile(os.path.join(path, ".claude-plugin", "plugin.json")) else None


def differences(root):
    """[(row, why)] for every carried file that differs from its source's copy, and the names of the
    sources that were not beside this core (so their rows were not compared)."""
    core = core_of(root)
    out, missing = [], set()
    for path, source, _ in carried(root):
        theirs_root = canonical(source, root)
        if theirs_root is None:
            missing.add(source)
            continue
        mine = os.path.join(root, path.replace("{core}", core))
        theirs = os.path.join(theirs_root, path.replace("{core}", source))
        if not os.path.isfile(mine):
            out.append((path, "absent from %s" % core))
        elif not os.path.isfile(theirs):
            out.append((path, "absent from %s" % source))
        elif digest(mine) != digest(theirs):
            out.append((path, "differs from %s" % source))
    return out, sorted(missing)


def skip_reason(missing):
    return ("not beside this core (the installed shape): %s; those rows cannot be compared here, and this "
            "is reported as skipped, not passed" % ", ".join(missing))


class TheList(unittest.TestCase):

    def test_every_row_is_well_formed_and_listed_once(self):
        rows = listed(plugin_root())
        self.assertTrue(rows)
        paths = [p for p, _, _ in rows]
        self.assertEqual(len(paths), len(set(paths)), "a path is listed twice")

    def test_every_carried_file_exists_here(self):
        root = plugin_root()
        for path, _, _ in carried(root):
            self.assertTrue(os.path.isfile(os.path.join(root, path.replace("{core}", core_of(root)))), path)

    def test_the_list_names_itself_the_loop_and_the_trace(self):
        paths = [p for p, _, _ in listed(plugin_root())]
        for path in ("skills/{core}/references/back-files.txt", "skills/{core}/references/back-loop.md",
                     "skills/{core}/references/trace.schema.json", "skills/{core}/scripts/back_core/trace.py",
                     "skills/{core}/scripts/validate-trace.py"):
            self.assertIn(path, paths)

    def test_every_station_core_and_back_core_module_is_listed(self):
        root = plugin_root()
        paths = set(p for p, _, _ in listed(root))
        for package in ("station_core", "back_core"):
            folder = os.path.join(root, "skills", core_of(root), "scripts", package)
            for name in sorted(os.listdir(folder)):
                if name.endswith(".py"):
                    self.assertIn("skills/{core}/scripts/%s/%s" % (package, name), paths, name)

    def test_the_seeded_rows_are_carried_whole_or_not_at_all(self):
        root = plugin_root()
        seeded = [p for p, _, s in listed(root) if s]
        present = [p for p in seeded if os.path.isfile(os.path.join(root, p.replace("{core}", core_of(root))))]
        if has_family(root):
            self.assertEqual(present, seeded)
        else:
            self.assertEqual(present, [], "a seeded frame file in a core with no family yet")


class EqualToTheSources(unittest.TestCase):

    def test_every_carried_file_is_byte_identical_to_its_source(self):
        root = plugin_root()
        found, missing = differences(root)
        self.assertEqual(found, [])
        if missing:
            self.skipTest(skip_reason(missing))

    def test_the_list_itself_is_vertical_v2s(self):
        root = plugin_root()
        theirs = canonical("vertical-v2", root)
        if theirs is None:
            self.skipTest(skip_reason(["vertical-v2"]))
        self.assertEqual(digest(list_path(root)), digest(list_path(theirs)))


class TheThreeBackCores(unittest.TestCase):

    def test_the_other_back_cores_hold_the_same_files(self):
        root = plugin_root()
        present = [c for c in BACK_CORES if canonical(c, root) is not None]
        if len(present) < 2:
            self.skipTest("the checkout holds %s of the three back cores" % (", ".join(present) or "none"))
        for path, _, seeded in listed(root):
            digests = {}
            for core in present:
                folder = canonical(core, root)
                if seeded and not has_family(folder):
                    continue
                target = os.path.join(folder, path.replace("{core}", core))
                self.assertTrue(os.path.isfile(target), (core, path))
                digests[core] = digest(target)
            self.assertLessEqual(len(set(digests.values())), 1, (path, digests))


class OneChangedByte(unittest.TestCase):
    """The comparison is proved on a scratch copy with one byte changed, so a green run is not a blind one."""

    def setUp(self):
        self.tmp = testlib.make_scratch("back-equal-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def copy_of(self):
        import shutil
        root = plugin_root()
        if canonical("precon-v2", root) is None:
            self.skipTest(skip_reason(["precon-v2"]))
        siblings = os.path.join(self.tmp, "plugins")
        mine = os.path.join(siblings, core_of(root))
        shutil.copytree(root, mine, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(canonical("precon-v2", root), os.path.join(siblings, "precon-v2"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        vertical = canonical("vertical-v2", root)
        if core_of(root) != "vertical-v2" and vertical is not None:
            shutil.copytree(vertical, os.path.join(siblings, "vertical-v2"),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        return mine

    def flip(self, path):
        with open(path, "rb") as fh:
            data = bytearray(fh.read())
        data[len(data) // 2] ^= 0x01
        with open(path, "wb") as fh:
            fh.write(bytes(data))

    def test_a_copied_file_with_one_byte_changed_is_found(self):
        mine = self.copy_of()
        core = core_of(mine)
        target = os.path.join(mine, "skills", core, "scripts", "station_core", "hunt.py")
        self.flip(target)
        old = os.environ.get("BACK_EQUAL_ROOT")
        os.environ["BACK_EQUAL_ROOT"] = mine
        try:
            found, _ = differences(mine)
        finally:
            if old is None:
                del os.environ["BACK_EQUAL_ROOT"]
            else:
                os.environ["BACK_EQUAL_ROOT"] = old
        self.assertEqual(found, [("skills/{core}/scripts/station_core/hunt.py", "differs from precon-v2")])

    def test_the_unchanged_copy_has_no_difference(self):
        mine = self.copy_of()
        found, _ = differences(mine)
        self.assertEqual(found, [])

    def test_the_installed_shape_is_skipped_never_passed(self):
        root = plugin_root()
        import shutil
        lone = os.path.join(self.tmp, "cache", "market", core_of(root), "0.1.0")
        shutil.copytree(root, lone, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        found, missing = differences(lone)
        self.assertEqual(found, [])
        self.assertIn("precon-v2", missing)
        self.assertIn("skipped, not passed", skip_reason(missing))


if __name__ == "__main__":
    unittest.main()
