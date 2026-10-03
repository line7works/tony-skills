"""The vendored CommonMark reader (the E15 lane contract A13; contract section 15, "Runtime").

`scripts/vendor/` holds `markdown-it-py` 3.0.0 and `mdurl` 0.1.2 unpacked from their wheels, unmodified, each
package's license files beside it in its `.dist-info` folder (the wheel's other metadata is left out and named), and
`vendor/VENDOR.json`, which names each package, its version, its wheel's file name and sha256, and every vendored
file's path and sha256. Nothing is installed and nothing is fetched at run time.

This test holds the vendored tree byte for byte to `VENDOR.json` (no file added, changed or missing), holds each
wheel's sha256 to A13's pins (PyPI's published digests), holds that only wheel metadata was left out, and holds the
import seam: `vertical_core/commonmark.py` is the only module that imports the reader, it loads the
vendored copy under the running interpreter with the `commonmark` preset, and it leaves `sys.path` as it found it.
"""
import hashlib
import json
import os
import re
import sys
import unittest

import testlib

testlib.add_scripts_to_path()

VENDOR = os.path.join(testlib.SCRIPTS, "vendor")
MANIFEST = os.path.join(VENDOR, "VENDOR.json")
# A13's pins: each wheel's sha256, equal to PyPI's published digest for that file
PINS = {
    "markdown-it-py": ("3.0.0", "markdown_it_py-3.0.0-py3-none-any.whl",
                       "355216845c60bd96232cd8d8c40e8f9765cc86f46880e43a8fd22dc1a1a8cab1"),
    "mdurl": ("0.1.2", "mdurl-0.1.2-py3-none-any.whl",
              "84008a41e51615a49fc9966191ff91509e3c40b939176e643fd50a5c2196b8f8"),
}
IMPORTS = re.compile(r"^\s*(?:import|from)\s+(?:markdown_it|mdurl)\b", re.M)


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def tree(root):
    """Every regular file under `root` (a `__pycache__` folder is never part of the vendored tree), as paths
    relative to it with `/`; a link anywhere is reported as one."""
    out, links = [], []
    for base, dirs, names in os.walk(root):
        for name in list(dirs):
            if os.path.islink(os.path.join(base, name)):
                links.append(os.path.relpath(os.path.join(base, name), root))
        dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not os.path.islink(os.path.join(base, d)))
        for name in sorted(names):
            full = os.path.join(base, name)
            if os.path.islink(full):
                links.append(os.path.relpath(full, root))
                continue
            out.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return out, links


class TheManifest(unittest.TestCase):

    def setUp(self):
        self.assertTrue(os.path.isfile(MANIFEST), "no vendor/VENDOR.json")
        with open(MANIFEST, encoding="utf-8") as fh:
            self.manifest = json.load(fh)

    def test_the_wheels_are_a13s_pins(self):
        packages = dict((p["name"], (p["version"], p["wheel"], p["wheel_sha256"])) for p in self.manifest["packages"])
        self.assertEqual(packages, PINS)

    def test_the_vendored_tree_is_the_manifest_byte_for_byte(self):
        files, links = tree(VENDOR)
        self.assertEqual(links, [])
        listed = dict((f["path"], f["sha256"]) for f in self.manifest["files"])
        self.assertEqual(len(listed), len(self.manifest["files"]), "a path is listed twice")
        self.assertEqual(sorted(set(files) - {"VENDOR.json"}), sorted(listed))
        for path, digest in sorted(listed.items()):
            self.assertEqual(sha256(os.path.join(VENDOR, *path.split("/"))), digest, path)

    def test_each_file_belongs_to_a_listed_package(self):
        names = set(p["name"] for p in self.manifest["packages"])
        for entry in self.manifest["files"]:
            self.assertIn(entry["package"], names, entry["path"])

    def test_only_wheel_metadata_is_left_out(self):
        """Every file of each package folder is vendored; what the manifest says was left out of a wheel is that
        wheel's own metadata in its .dist-info folder (never a module and never a license file)."""
        for package in self.manifest["packages"]:
            for path in package["left_out"]:
                self.assertTrue(path.startswith(package["dist_info"] + "/"), path)
                self.assertFalse(os.path.basename(path).startswith("LICENSE"), path)
                self.assertFalse(path.endswith(".py"), path)
            folder = [f["path"] for f in self.manifest["files"] if f["path"].startswith(package["package_folder"] + "/")]
            self.assertTrue(any(p.endswith("/__init__.py") for p in folder), package["name"])

    def test_each_package_keeps_its_license_files(self):
        for package in self.manifest["packages"]:
            licenses = [f["path"] for f in self.manifest["files"]
                        if f["package"] == package["name"] and f["path"].startswith(package["dist_info"] + "/LICENSE")]
            self.assertTrue(licenses, package["name"])
            for path in licenses:
                self.assertIn("MIT", testlib.read_text(os.path.join(VENDOR, *path.split("/"))), path)


class TheImportSeam(unittest.TestCase):

    def test_only_the_commonmark_module_imports_the_reader(self):
        found = []
        for base, dirs, names in os.walk(testlib.SCRIPTS):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "vendor"))
            for name in names:
                if name.endswith(".py"):
                    full = os.path.join(base, name)
                    if IMPORTS.search(testlib.read_text(full)):
                        found.append(os.path.relpath(full, testlib.SCRIPTS).replace(os.sep, "/"))
        found = [f for f in found if f != "tests/test_vendor.py"]
        self.assertEqual(found, ["vertical_core/commonmark.py"])

    def test_the_reader_is_the_vendored_copy_under_this_interpreter(self):
        before = list(sys.path)
        from vertical_core import commonmark  # noqa: E402
        identity = commonmark.identity()
        self.assertEqual(sys.path, before)
        self.assertEqual(identity["preset"], "commonmark")
        self.assertEqual(identity["versions"], {"markdown_it": "3.0.0", "mdurl": "0.1.2"})
        real = os.path.realpath(VENDOR) + os.sep
        for name, path in identity["files"].items():
            self.assertTrue(os.path.realpath(path).startswith(real), (name, path))
        self.assertEqual(identity["python"][:2], list(sys.version_info[:2]))

    def test_the_preset_is_commonmark(self):
        """No table, no strikethrough, raw HTML on: the commonmark preset, not the default one."""
        from vertical_core import commonmark  # noqa: E402
        kinds = [t.type for t in commonmark.tokens("| a |\n|---|\n| b |\n\n~~x~~ <b>y</b>\n")]
        self.assertNotIn("table_open", kinds)
        inline = [t for t in commonmark.tokens("~~x~~ <b>y</b>\n") if t.type == "inline"][0]
        self.assertNotIn("s_open", [c.type for c in inline.children])
        self.assertIn("html_inline", [c.type for c in inline.children])


if __name__ == "__main__":
    unittest.main()
