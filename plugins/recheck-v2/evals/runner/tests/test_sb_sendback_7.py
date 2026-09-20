"""Send-back 7: the wall's read roots for a binary reached through a plain shell wrapper.

The measured failure (control room, 2026-09-19, record
`native-read-boundary/codex/harness-20260919T235910Z`): the walled Codex launch exited 126 in
one second with

    .../bin/codex: line 5: <npm prefix>/bin/codex: Operation not permitted
    .../bin/codex: line 5: exec: <npm prefix>/bin/codex: cannot execute: Operation not permitted

`_binary_read_roots` resolved `codex` with `which` + `os.path.realpath`. On that Mac the PATH
entry is a PLAIN `sh` file (not a symlink) whose only command is `exec <absolute path> "$@"`,
and the realpath of a plain file is itself - so the read root became the wrapper's own
directory and nothing under the npm prefix was allowed. The wrapper then exec'd a symlink
inside a denied subtree; resolving that symlink needs metadata reads of its ancestors, so the
exec itself was refused.

What these tests pin, with a FAKE layout built by the test and no machine path anywhere:

1. a plain `exec <absolute path> "$@"` wrapper is FOLLOWED (bounded, loop-safe), and the
   wrapper's own directory stays a read root;
2. a node-package executable's read root is its PACKAGE ROOT, not the `bin` directory the
   old "dirname of the real file" rule gave, so the native binary the package spawns from
   `node_modules/.../vendor/.../bin/` is inside an allowed subtree;
3. the directory of a symlink the chain passes through after a wrapper is a read root too,
   because exec'ing that symlink needs its ancestors readable;
4. nothing above changes the shape a plain symlink resolution produces - Claude Code's own
   (`<share>/claude/versions/<v>`) is asserted unchanged;
5. a wrapper whose `exec` target is relative, or that carries any second command, is NOT
   followed: it is treated exactly as it is today.

Standard library only, Python 3.9, runs from any working directory. No model, no harness, no
launch: every assertion is against `runner._binary_read_roots` over a directory tree this file
writes. Nothing here opens `evals/answer-key/`, the held-out set, or any routing request.
"""
import os
import shutil
import unittest

from testlib import runner, scratch_root


PACKAGE_JSON = '{"name": "@openai/codex", "version": "0.0.0-test", "bin": {"codex": ' \
               '"bin/codex.js"}}\n'


def needs(name, why=None):
    """A `wall-needs.json` `binaries` block naming one binary."""
    entry = {"name": name}
    if why:
        entry["why"] = why
    return {"binaries": [entry]}


def paths(rows):
    return [row["path"] for row in rows]


class FakeInstall(unittest.TestCase):
    """A scratch tree plus a PATH that names only it, restored after every test."""

    def setUp(self):
        self.root = os.path.realpath(scratch_root())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.previous_path = os.environ.get("PATH")
        self.addCleanup(self.restore_path)

    def restore_path(self):
        if self.previous_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = self.previous_path

    def on_path(self, *directories):
        """Only these directories, so nothing this Mac happens to have installed is reached."""
        os.environ["PATH"] = ":".join(directories)

    # ---- fixture pieces

    def executable(self, path, text):
        runner.ensure_dir(os.path.dirname(path))
        runner.write_text(path, text)
        os.chmod(path, 0o755)
        return path

    def wrapper(self, path, body):
        return self.executable(path, "#!/bin/sh\n# a comment the reader skips\n%s\n" % body)

    def exec_wrapper(self, path, target):
        return self.wrapper(path, 'exec %s "$@"' % target)

    def symlink(self, path, target):
        runner.ensure_dir(os.path.dirname(path))
        os.symlink(target, path)
        return path

    def node_package(self, scope="@openai", package="codex", platform="codex-darwin-arm64"):
        """`<root>/npm/lib/node_modules/<scope>/<package>/` with a bin, a package.json and the
        platform package whose vendored native binary the js entry point spawns."""
        modules = os.path.join(self.root, "npm", "lib", "node_modules")
        package_root = os.path.join(modules, scope, package)
        runner.write_text(os.path.join(package_root, "package.json"), PACKAGE_JSON)
        entry = self.executable(os.path.join(package_root, "bin", "%s.js" % package),
                                "#!/usr/bin/env node\n// a fake entry point\n")
        native = self.executable(
            os.path.join(package_root, "node_modules", scope, platform, "vendor",
                         "aarch64-apple-darwin", "bin", package),
            "#!/bin/sh\nexit 0\n")
        link_dir = os.path.join(self.root, "npm", "bin")
        runner.ensure_dir(link_dir)
        link = os.path.join(link_dir, package)
        os.symlink(os.path.relpath(entry, link_dir), link)
        return {"package_root": package_root, "entry": entry, "native": native,
                "link": link, "link_dir": link_dir}


class WrapperToNodePackageTest(FakeInstall):
    """The measured shape: wrapper -> symlink -> js entry point inside a node package."""

    def setUp(self):
        super(WrapperToNodePackageTest, self).setUp()
        self.install = self.node_package()
        self.bin = os.path.join(self.root, "bin")
        self.wrapper_path = self.exec_wrapper(os.path.join(self.bin, "codex"),
                                              self.install["link"])
        self.on_path(self.bin)

    def rows(self):
        return runner._binary_read_roots(needs("codex"))

    def test_the_package_root_is_a_read_root(self):
        self.assertIn(self.install["package_root"], paths(self.rows()))

    def test_the_bin_directory_of_the_package_is_NOT_the_read_root(self):
        """The old rule's answer. It would leave the native binary outside every allow."""
        self.assertNotIn(os.path.dirname(self.install["entry"]), paths(self.rows()))

    def test_the_native_binary_the_package_spawns_is_inside_an_allowed_root(self):
        allowed = paths(self.rows())
        self.assertTrue(
            any(runner.path_contains(root, self.install["native"]) for root in allowed),
            "%s is under none of %s" % (self.install["native"], allowed))

    def test_the_symlinks_own_directory_is_a_read_root(self):
        self.assertIn(self.install["link_dir"], paths(self.rows()))

    def test_the_wrappers_own_directory_stays_a_read_root(self):
        self.assertIn(self.bin, paths(self.rows()))

    def test_every_hop_is_recorded_in_a_why_so_the_record_shows_the_chain(self):
        why = " ".join(row["why"] for row in self.rows())
        for hop in (self.wrapper_path, self.install["link"], self.install["entry"]):
            self.assertIn(hop, why, hop)

    def test_the_setups_own_why_survives(self):
        rows = runner._binary_read_roots(needs("codex", "the harness itself, as declared"))
        self.assertTrue(any("the harness itself, as declared" in row["why"] for row in rows))

    def test_no_row_names_a_path_twice(self):
        got = paths(self.rows())
        self.assertEqual(len(got), len(set(got)), got)


class TodaysRuleIsUnchangedTest(FakeInstall):
    """Everything that is not a wrapper into a node package resolves exactly as before."""

    def test_the_claude_code_shape_is_unchanged(self):
        """`<bin>/claude` -> `<share>/claude/versions/<v>`, a single-file executable."""
        versions = os.path.join(self.root, "share", "claude", "versions")
        real = self.executable(os.path.join(versions, "2.1.278"), "a single-file bundle\n")
        binaries = os.path.join(self.root, "bin")
        self.symlink(os.path.join(binaries, "claude"), real)
        self.on_path(binaries)
        self.assertEqual(paths(runner._binary_read_roots(needs("claude"))), [versions, real])

    def test_a_symlink_chain_without_a_wrapper_still_resolves_as_before(self):
        real = self.executable(os.path.join(self.root, "opt", "tool", "tool"), "#!/bin/sh\n")
        middle = self.symlink(os.path.join(self.root, "middle", "tool"), real)
        binaries = os.path.join(self.root, "bin")
        self.symlink(os.path.join(binaries, "tool"), middle)
        self.on_path(binaries)
        rows = runner._binary_read_roots(needs("tool"))
        self.assertEqual(paths(rows), [os.path.dirname(real), real])
        self.assertNotIn(os.path.dirname(middle), paths(rows))
        self.assertNotIn(binaries, paths(rows))

    def test_a_wrapper_whose_exec_target_is_RELATIVE_is_not_followed(self):
        install = self.node_package()
        binaries = os.path.join(self.root, "bin")
        wrapper = self.exec_wrapper(os.path.join(binaries, "codex"),
                                    os.path.relpath(install["link"], binaries))
        self.on_path(binaries)
        rows = runner._binary_read_roots(needs("codex"))
        self.assertEqual(paths(rows), [binaries, wrapper])

    def test_a_wrapper_that_carries_a_SECOND_command_is_not_followed(self):
        install = self.node_package()
        binaries = os.path.join(self.root, "bin")
        wrapper = self.wrapper(os.path.join(binaries, "codex"),
                               'echo "a second command"\nexec %s "$@"' % install["link"])
        self.on_path(binaries)
        self.assertEqual(paths(runner._binary_read_roots(needs("codex"))), [binaries, wrapper])

    def test_a_wrapper_whose_exec_line_takes_no_arguments_is_not_followed(self):
        """`exec <path>` without `"$@"` is not the wrapper shape; it is left alone."""
        install = self.node_package()
        binaries = os.path.join(self.root, "bin")
        wrapper = self.wrapper(os.path.join(binaries, "codex"), "exec %s" % install["link"])
        self.on_path(binaries)
        self.assertEqual(paths(runner._binary_read_roots(needs("codex"))), [binaries, wrapper])

    def test_a_binary_that_is_not_on_PATH_contributes_nothing(self):
        self.on_path(os.path.join(self.root, "empty"))
        self.assertEqual(runner._binary_read_roots(needs("codex")), [])

    def test_an_executable_outside_any_node_modules_keeps_the_directory_rule(self):
        """A wrapper is followed; the package-root rule does not apply outside node_modules."""
        real = self.executable(os.path.join(self.root, "opt", "tool", "bin", "tool"),
                               "#!/bin/sh\n")
        binaries = os.path.join(self.root, "bin")
        self.exec_wrapper(os.path.join(binaries, "tool"), real)
        self.on_path(binaries)
        self.assertIn(os.path.dirname(real), paths(runner._binary_read_roots(needs("tool"))))


class WrapperFollowingIsBoundedTest(FakeInstall):
    """A chain cannot hang the resolver or walk forever."""

    def test_a_loop_of_wrappers_terminates(self):
        binaries = os.path.join(self.root, "bin")
        first = os.path.join(binaries, "tool")
        second = os.path.join(binaries, "tool-b")
        self.exec_wrapper(first, second)
        self.exec_wrapper(second, first)
        self.on_path(binaries)
        rows = runner._binary_read_roots(needs("tool"))
        self.assertIn(binaries, paths(rows))

    def test_a_chain_longer_than_the_bound_stops_at_the_bound(self):
        binaries = os.path.join(self.root, "bin")
        links = [os.path.join(binaries, "tool")] + [
            os.path.join(self.root, "hop%d" % index, "tool") for index in range(1, 9)]
        for current, following in zip(links, links[1:]):
            self.exec_wrapper(current, following)
        self.executable(links[-1], "#!/bin/sh\nexit 0\n")
        self.on_path(binaries)
        rows = runner._binary_read_roots(needs("tool"))
        reached = [os.path.dirname(link) for link in links]
        followed = [directory for directory in reached if directory in paths(rows)]
        self.assertLessEqual(len(followed), runner.WRAPPER_HOPS + 1, followed)
        self.assertNotIn(os.path.dirname(links[-1]), paths(rows))


class QuotedWrapperTest(FakeInstall):
    """`exec "<path>" "$@"` is the same wrapper with the target quoted."""

    def test_a_quoted_absolute_target_is_followed(self):
        install = self.node_package()
        binaries = os.path.join(self.root, "bin")
        self.wrapper(os.path.join(binaries, "codex"),
                     'exec "%s" "$@"' % install["link"])
        self.on_path(binaries)
        self.assertIn(install["package_root"], paths(runner._binary_read_roots(needs("codex"))))


class NotAWrapperTest(FakeInstall):
    """Only a small text file with one `exec` command is read as a wrapper."""

    def test_a_binary_file_is_never_read_as_a_wrapper(self):
        binaries = os.path.join(self.root, "bin")
        target = self.executable(os.path.join(self.root, "opt", "real"), "#!/bin/sh\n")
        path = os.path.join(binaries, "tool")
        runner.ensure_dir(binaries)
        with open(path, "wb") as handle:
            handle.write(b"\x7fELF\x00\x00exec %s \"$@\"\n" % target.encode("utf-8"))
        os.chmod(path, 0o755)
        self.on_path(binaries)
        self.assertEqual(paths(runner._binary_read_roots(needs("tool"))), [binaries, path])

    def test_a_symlink_is_never_read_as_a_wrapper_even_when_its_text_looks_like_one(self):
        """A symlink already resolves; reading its target's text must not add a second hop."""
        wrapper_text = self.executable(os.path.join(self.root, "opt", "inner"),
                                       '#!/bin/sh\nexec /usr/bin/true "$@"\n')
        binaries = os.path.join(self.root, "bin")
        self.symlink(os.path.join(binaries, "tool"), wrapper_text)
        self.on_path(binaries)
        rows = runner._binary_read_roots(needs("tool"))
        self.assertEqual(paths(rows), [os.path.dirname(wrapper_text), wrapper_text])


if __name__ == "__main__":
    unittest.main()
