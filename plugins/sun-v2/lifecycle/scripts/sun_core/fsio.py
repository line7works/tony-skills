"""The one seam to the file system (the frame's RUN-4, LOG-1, OP-3, OP-4, SEC-7).

Every read and every write the lifecycle core makes of this machine goes through one `FS` object, so
that a test can stand a recording file system in its place and show, from that record and not from
the order of the code, which read stood before which write and before the first byte of output.

`FS` here is the real one. Each method announces what it is about to do, and what it has done, to
`self.hook(stage, op, path)` when a hook is set: `pre` before anything changes, `mid` for a mutation
whose bytes are written and not yet synced, `post` once it is durable. A read announces `read` once.
The core never sets the hook; a test's world does.

Durability (LOG-1): `append` and `write_new` write, flush and sync the file and then its directory;
`replace_atomic` builds a temporary file beside the target, syncs it, renames it over the target and
syncs the directory. `rename_noreplace` is the exclusive rename C1 and C7 need: it fails where
anything is at the target, an empty folder included.
"""
import ctypes
import ctypes.util
import errno
import fcntl
import hashlib
import json
import os
import stat as statmod
import sys

OWNER_FILE = 0o600
OWNER_DIR = 0o700
_RENAME_EXCL = 0x00000004      # Darwin renamex_np
_RENAME_NOREPLACE = 0x00000001  # Linux renameat2
_AT_FDCWD = -100
_O_SEARCH = getattr(os, "O_SEARCH", 0x40100000 if sys.platform == "darwin" else None)   # Darwin: O_EXEC | O_DIRECTORY


class Exists(OSError):
    """Something is at the place an exclusive create or rename needs empty."""


class NoExclusiveRename(RuntimeError):
    """This system offers no rename that fails on an existing target; C1 and C7 are then not run."""


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json(doc):
    return json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def pretty_json(doc):
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _libc():
    return ctypes.CDLL(ctypes.util.find_library("c") or None, use_errno=True)


def _exclusive_rename(src, dst):
    libc = _libc()
    a, b = os.fsencode(src), os.fsencode(dst)
    if sys.platform == "darwin":
        fn = getattr(libc, "renamex_np", None)
        if fn is None:
            raise NoExclusiveRename("renamex_np")
        fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rc = fn(a, b, _RENAME_EXCL)
    else:
        fn = getattr(libc, "renameat2", None)
        if fn is None:
            raise NoExclusiveRename("renameat2")
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rc = fn(_AT_FDCWD, a, _AT_FDCWD, b, _RENAME_NOREPLACE)
    if rc != 0:
        code = ctypes.get_errno()
        if code in (errno.EEXIST, errno.ENOTEMPTY):
            raise Exists(code, os.strerror(code), dst)
        raise OSError(code, os.strerror(code), dst)


class FS(object):
    """The real file system, announcing each act to `hook` when one is set."""

    def __init__(self, hook=None):
        self.hook = hook

    def note(self, stage, op, path, **more):
        if self.hook is not None:
            self.hook(stage, op, path, **more)

    # ---- reads ----------------------------------------------------------------------------------
    def read(self, path):
        self.note("read", "read", path)
        with open(path, "rb") as fh:
            return fh.read()

    def read_text(self, path):
        return self.read(path).decode("utf-8")

    def read_json(self, path):
        return json.loads(self.read_text(path))

    def read_first_record(self, path, most):
        """The bytes of a file up to its first newline and no further (RUN-5: the look reads a journal's record of a run's
        opening "and nothing else of a run it has not found"): (the line without its newline, True); (every byte, False)
        where the file holds no newline; (the first `most` bytes, None) where no newline stands within them. Read a byte
        at a time, so that nothing after the newline is taken in."""
        self.note("read", "read-first-record", path)
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            out = bytearray()
            while len(out) < most:
                byte = os.read(fd, 1)
                if not byte:
                    return bytes(out), False
                if byte == b"\n":
                    return bytes(out), True
                out += byte
            return bytes(out), None
        finally:
            os.close(fd)

    def lexists(self, path):
        self.note("read", "lexists", path)
        return os.path.lexists(path)

    def lstat(self, path):
        self.note("read", "lstat", path)
        return os.lstat(path)

    def listdir(self, path):
        self.note("read", "listdir", path)
        return sorted(os.listdir(path))

    def isdir(self, path):
        self.note("read", "lstat", path)
        try:
            return statmod.S_ISDIR(os.lstat(path).st_mode)
        except OSError:
            return False

    def isfile(self, path):
        self.note("read", "lstat", path)
        try:
            return statmod.S_ISREG(os.lstat(path).st_mode)
        except OSError:
            return False

    def is_program_file(self, path):
        """A file of that name stands there, the link it may be followed (SEC-3: the runner starts the first file
        of the declared name it finds on the search list)."""
        self.note("read", "stat", path)
        try:
            return statmod.S_ISREG(os.stat(path).st_mode)
        except OSError:
            return False

    def islink(self, path):
        self.note("read", "lstat", path)
        return os.path.islink(path)

    def realpath(self, path):
        self.note("read", "realpath", path)
        return os.path.realpath(path)

    def identity(self, path):
        """The file system's own identity for the object at `path`, with its volume; None when
        nothing is there. A rename keeps it and a copy does not (the frame's Part 2)."""
        self.note("read", "identity", path)
        try:
            st = os.lstat(path)
        except OSError:
            return None
        return {"volume": st.st_dev, "object": st.st_ino}

    def mode(self, path):
        self.note("read", "lstat", path)
        return statmod.S_IMODE(os.lstat(path).st_mode)

    def walk(self, root):
        """Every path under `root` (files, folders and links), sorted, without following links."""
        self.note("read", "walk", root)
        out = []
        for base, dirs, files in os.walk(root, followlinks=False):
            dirs.sort()
            for name in sorted(dirs + files):
                out.append(os.path.join(base, name))
        return sorted(out)

    def volume(self, path):
        self.note("read", "lstat", path)
        probe = path
        while not os.path.lexists(probe):
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        return os.lstat(probe).st_dev

    # ---- writes ---------------------------------------------------------------------------------
    def _sync_dir(self, folder):
        try:
            fd = os.open(folder or ".", os.O_RDONLY)
        except PermissionError:
            if _O_SEARCH is None:
                raise
            # a folder its owner may search and write and not list (RUN-5's fixture of a folder of run directories that
            # cannot be listed, A59): opened for search alone, and synced all the same
            fd = os.open(folder or ".", _O_SEARCH)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def mkdir(self, path, mode=OWNER_DIR):
        self.note("pre", "mkdir", path)
        os.mkdir(path, mode)
        os.chmod(path, mode)
        self.note("mid", "mkdir", path)
        self._sync_dir(os.path.dirname(path))
        self.note("post", "mkdir", path)

    def makedirs(self, path, mode=OWNER_DIR):
        missing = []
        probe = path
        while not os.path.lexists(probe):
            missing.append(probe)
            probe = os.path.dirname(probe)
        for item in reversed(missing):
            self.mkdir(item, mode)

    def write_new(self, path, data, mode=OWNER_FILE):
        """A new file, owner-only from its first byte; fails where anything is at the path."""
        self.note("pre", "create", path)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
        except FileExistsError as exc:
            raise Exists(exc.errno, exc.strerror, path)
        try:
            os.fchmod(fd, mode)
            os.write(fd, data)
            self.note("mid", "create", path)
            os.fsync(fd)
        finally:
            os.close(fd)
        self._sync_dir(os.path.dirname(path))
        self.note("post", "create", path)

    def append(self, path, data, mode=OWNER_FILE):
        """Append, flush and sync the file together with its directory (LOG-1)."""
        self.note("pre", "append", path, size=len(data))
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0), mode)
        try:
            os.write(fd, data)
            self.note("mid", "append", path, size=len(data))
            os.fsync(fd)
        finally:
            os.close(fd)
        self._sync_dir(os.path.dirname(path))
        self.note("post", "append", path, size=len(data))

    def truncate(self, path, size):
        """Cut a cut-off last record away before the next append (LOG-1's one tolerated state)."""
        self.note("pre", "truncate", path, size=size)
        fd = os.open(path, os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            os.ftruncate(fd, size)
            os.fsync(fd)
        finally:
            os.close(fd)
        self.note("post", "truncate", path, size=size)

    def replace_atomic(self, path, data, mode=OWNER_FILE):
        """The whole file replaced by one rename: all of `data` or the file as it was."""
        tmp = path + ".new"
        self.note("pre", "replace", path)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), mode)
        try:
            os.fchmod(fd, mode)
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        self.note("mid", "replace", path, staged=tmp)
        os.replace(tmp, path)
        self._sync_dir(os.path.dirname(path))
        self.note("post", "replace", path)

    def rename_noreplace(self, src, dst):
        """Rename that fails if anything is at `dst` (C1, C7); the directory is synced after."""
        self.note("pre", "rename", dst, source=src)
        _exclusive_rename(src, dst)
        self.note("mid", "rename", dst, source=src)
        self._sync_dir(os.path.dirname(dst))
        if os.path.dirname(src) != os.path.dirname(dst):
            self._sync_dir(os.path.dirname(src))
        self.note("post", "rename", dst, source=src)

    def swap(self, staged, path):
        """C3's swap: the staged file takes the old file's place (the caller holds the file's lock
        and has checked the old file's hash)."""
        self.note("pre", "swap", path, source=staged)
        os.replace(staged, path)
        self.note("mid", "swap", path, source=staged)
        self._sync_dir(os.path.dirname(path))
        self.note("post", "swap", path, source=staged)

    def fill_staged(self, fd, staged, data):
        """A lock's record staged beside its place, filled again through the descriptor that holds it (a file a killed
        taker left there); it is at no lock's place while it is written."""
        self.note("pre", "write", staged)
        os.ftruncate(fd, 0)
        os.pwrite(fd, data, 0)
        os.fsync(fd)
        self.note("post", "write", staged)

    def replace_into(self, staged, path):
        """A lock's new record put at its place by one rename over the file there (RUN-2, A41): another start reads the
        record as it was or the new record whole, never a part of one."""
        self.note("pre", "replace-record", path, source=staged)
        os.replace(staged, path)
        self.note("mid", "replace-record", path, source=staged)
        self._sync_dir(os.path.dirname(path))
        self.note("post", "replace-record", path, source=staged)

    def chmod(self, path, mode):
        self.note("pre", "chmod", path)
        os.chmod(path, mode)
        self.note("post", "chmod", path)

    def remove(self, path):
        self.note("pre", "remove", path)
        os.remove(path)
        self.note("mid", "remove", path)
        self._sync_dir(os.path.dirname(path))
        self.note("post", "remove", path)

    def rmtree(self, path):
        """Remove a folder the run made, deepest first; each removal is announced on its own."""
        for item in sorted(self.walk(path), key=lambda p: -len(p)):
            if os.path.isdir(item) and not os.path.islink(item):
                self.rmdir(item)
            else:
                self.remove(item)
        self.rmdir(path)

    def rmdir(self, path):
        self.note("pre", "remove", path)
        os.rmdir(path)
        self.note("mid", "remove", path)
        self._sync_dir(os.path.dirname(path))
        self.note("post", "remove", path)

    # ---- locks ----------------------------------------------------------------------------------
    def lock_exclusive(self, path, create):
        """An advisory lock the system releases when its holder dies. Returns the open descriptor,
        or None where another holder has it. Never waits. With `create`, the lock's file is made
        when it is not there; the caller then checks it still is the file at the path."""
        self.note("read", "lock", path)
        flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        created = False
        if create:
            try:
                fd = os.open(path, flags | os.O_CREAT | os.O_EXCL, OWNER_FILE)
                created = True
            except FileExistsError:
                fd = os.open(path, flags)
        else:
            fd = os.open(path, flags)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return None
        try:
            same = os.fstat(fd).st_ino == os.stat(path).st_ino
        except OSError:
            same = False
        if not same:
            os.close(fd)
            return self.lock_exclusive(path, create)
        if created:
            try:
                self.note("post", "create", path)
            except BaseException:
                os.close(fd)
                raise
        return fd

    def unlock(self, fd, path, remove):
        """Release a lock; with `remove`, the lock's file goes while the lock is still held."""
        if remove:
            self.note("pre", "unlock-remove", path)
            try:
                os.remove(path)
            except OSError:
                pass
            self.note("post", "unlock-remove", path)
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
