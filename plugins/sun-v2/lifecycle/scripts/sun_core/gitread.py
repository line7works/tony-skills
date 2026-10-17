"""The commit of the tool's own files, as the tool reads it itself, in its own process (the frame's SEC-12, the
identity answer; SEC-4's hash row, "a commit it made or read on this machine").

It is read from the nearest repository at or above the folder of the tool's own files, and only where that
repository holds those files in its commit: each of the tool's own files stands in the commit's tree at its path,
with the same bytes. A repository that does not hold them, as one that a copy of the tool merely sits inside, is not
theirs, and nothing of it is answered. Where no repository holds them, or the repository cannot be read whole, the
answer is None, and the identity answer gives the tool's own fixed words for no commit.

Standard library only (RUN-1, A47): the repository's own files are read as git writes them, loose objects and packs
(index version 2, offset and reference deltas), loose and packed references, a worktree's `.git` file and its common
folder, and a repository's alternates. A repository of another object format is not read. Nothing here starts a
program, and nothing is written.
"""
import hashlib
import os
import struct
import zlib

HEX = "0123456789abcdef"
_TYPES = {1: b"commit", 2: b"tree", 3: b"blob", 4: b"tag"}


class Unreadable(Exception):
    """The repository cannot be read whole: nothing is answered from it."""


class _Disk(object):
    """This machine's files, read directly (the identity answer). SEC-10's check hands its own file system seam instead."""

    def read(self, path):
        with open(path, "rb") as fh:
            return fh.read()

    def isfile(self, path):
        return os.path.isfile(path)

    def isdir(self, path):
        return os.path.isdir(path)

    def listdir(self, path):
        return sorted(os.listdir(path))


DISK = _Disk()


def nearest(start, fs=DISK):
    """(top, git folder) of the nearest repository at or above `start`; None where none is."""
    folder = os.path.abspath(start)
    while True:
        dot = os.path.join(folder, ".git")
        if fs.isdir(dot):
            return folder, dot
        if fs.isfile(dot):
            text = fs.read(dot).decode("utf-8", "replace").strip()
            if not text.startswith("gitdir:"):
                raise Unreadable("a .git file that names no folder")
            target = text[len("gitdir:"):].strip()
            return folder, os.path.normpath(os.path.join(folder, target))
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent


class Repository(object):
    def __init__(self, top, gitdir, fs=DISK):
        self.top = top
        self.gitdir = gitdir
        self.fs = fs
        common = os.path.join(gitdir, "commondir")
        if fs.isfile(common):
            self.common = os.path.normpath(os.path.join(gitdir, fs.read(common).decode("utf-8").strip()))
        else:
            self.common = gitdir
        config = os.path.join(self.common, "config")
        if fs.isfile(config):
            text = fs.read(config).decode("utf-8", "replace").lower()
            if "objectformat" in text and "sha256" in text:
                raise Unreadable("another object format")
        self.object_dirs = [os.path.join(self.common, "objects")]
        alternates = os.path.join(self.common, "objects", "info", "alternates")
        if fs.isfile(alternates):
            for line in fs.read(alternates).decode("utf-8", "replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    self.object_dirs.append(os.path.normpath(os.path.join(self.object_dirs[0], line)))
        self._packs = None

    # ---- references -----------------------------------------------------------------------------
    def _loose_ref(self, name):
        for base in (self.gitdir, self.common):
            path = os.path.join(base, *name.split("/"))
            if self.fs.isfile(path):
                return self.fs.read(path).decode("utf-8", "replace").strip()
        return None

    def _packed_ref(self, name):
        path = os.path.join(self.common, "packed-refs")
        if not self.fs.isfile(path):
            return None
        for line in self.fs.read(path).decode("utf-8", "replace").splitlines():
            if not line or line[0] in "#^":
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip() == name:
                return parts[0].strip()
        return None

    def head(self):
        """The commit HEAD names; None where it names none yet."""
        value = self._loose_ref("HEAD")
        for _ in range(8):
            if value is None:
                return None
            if value.startswith("ref:"):
                name = value[4:].strip()
                value = self._loose_ref(name) or self._packed_ref(name)
                continue
            if len(value) == 40 and all(c in HEX for c in value):
                return value
            raise Unreadable("a reference that names no commit")
        raise Unreadable("a chain of references too long")

    # ---- objects --------------------------------------------------------------------------------
    def _loose(self, sha):
        for base in self.object_dirs:
            path = os.path.join(base, sha[:2], sha[2:])
            if self.fs.isfile(path):
                data = zlib.decompress(self.fs.read(path))
                head, _, body = data.partition(b"\0")
                kind, _, size = head.partition(b" ")
                if int(size) != len(body):
                    raise Unreadable("a loose object of the wrong size")
                return kind, body
        return None

    def packs(self):
        if self._packs is None:
            self._packs = []
            for base in self.object_dirs:
                folder = os.path.join(base, "pack")
                if not self.fs.isdir(folder):
                    continue
                for name in self.fs.listdir(folder):
                    if name.endswith(".idx") and self.fs.isfile(os.path.join(folder, name[:-4] + ".pack")):
                        self._packs.append(Pack(os.path.join(folder, name[:-4]), self.fs))
        return self._packs

    def read(self, sha):
        """(kind, body) of the object; raises Unreadable where it is in no place the repository keeps objects."""
        found = self._loose(sha)
        if found is not None:
            return found
        for pack in self.packs():
            offset = pack.offset_of(sha)
            if offset is not None:
                return pack.object_at(offset, self)
        raise Unreadable("an object the repository does not hold")

    def tree_of_commit(self, sha):
        kind, body = self.read(sha)
        if kind != b"commit" or not body.startswith(b"tree "):
            raise Unreadable("HEAD names no commit")
        return body[5:45].decode("ascii")

    def entries(self, tree_sha):
        """{name: (mode, sha)} of one tree."""
        kind, body = self.read(tree_sha)
        if kind != b"tree":
            raise Unreadable("a tree that is no tree")
        out, at = {}, 0
        while at < len(body):
            space = body.index(b" ", at)
            nul = body.index(b"\0", space)
            mode = body[at:space].decode("ascii")
            name = body[space + 1:nul].decode("utf-8", "surrogateescape")
            out[name] = (mode, body[nul + 1:nul + 21].hex())
            at = nul + 21
        return out


    # ---- what a commit holds, and what will be committed (SEC-10) --------------------------------
    def ref(self, name):
        """The commit a full reference name names (`refs/...` or `HEAD`), following symbolic references; None where the
        name names nothing."""
        value = self._loose_ref(name) if name == "HEAD" else (self._loose_ref(name) or self._packed_ref(name))
        for _ in range(8):
            if value is None:
                return None
            if value.startswith("ref:"):
                target = value[4:].strip()
                value = self._loose_ref(target) or self._packed_ref(target)
                continue
            if len(value) == 40 and all(c in HEX for c in value):
                return value
            raise Unreadable("a reference that names no commit")
        raise Unreadable("a chain of references too long")

    def commit(self, sha):
        """(tree, [parents], the commit object's own bytes)."""
        kind, body = self.read(sha)
        if kind != b"commit":
            raise Unreadable("an object that is no commit")
        tree, parents = None, []
        for line in body.split(b"\n\n", 1)[0].split(b"\n"):
            if line.startswith(b"tree "):
                tree = line[5:].decode("ascii")
            elif line.startswith(b"parent "):
                parents.append(line[7:].decode("ascii"))
        if tree is None:
            raise Unreadable("a commit that names no tree")
        return tree, parents, body

    def files(self, tree_sha, prefix=""):
        """{path: (mode, blob)} of every file a tree holds, at any depth; a submodule's commit is no file of it."""
        out = {}
        for name, (mode, sha) in sorted(self.entries(tree_sha).items()):
            here = prefix + name
            if mode in ("40000", "040000"):
                out.update(self.files(sha, here + "/"))
            elif mode != "160000":
                out[here] = (mode, sha)
        return out

    def index(self):
        """{path: [(mode, blob), ...]} of the index, every stage of a path in order: what a commit made now would hold
        (index versions 2 and 3; a repository whose index is of another version is not read). {} where there is none."""
        path = os.path.join(self.gitdir, "index")
        if not self.fs.isfile(path):
            return {}
        data = self.fs.read(path)
        if data[:4] != b"DIRC" or len(data) < 12:
            raise Unreadable("an index that is no index")
        version, count = struct.unpack(">II", data[4:12])
        if version not in (2, 3):
            raise Unreadable("an index of a version this reader does not know")
        out, at = {}, 12
        for _ in range(count):
            start = at
            mode = struct.unpack(">I", data[at + 24:at + 28])[0]
            sha = data[at + 40:at + 60].hex()
            flags = struct.unpack(">H", data[at + 60:at + 62])[0]
            at += 62
            if flags & 0x4000:
                if version < 3:
                    raise Unreadable("an extended entry in an index of version 2")
                at += 2
            nul = data.index(b"\0", at)
            name = data[at:nul].decode("utf-8", "surrogateescape")
            at = start + ((nul - start) // 8 + 1) * 8
            if (mode & 0o170000) == 0o160000:
                continue
            out.setdefault(name, []).append(("%o" % mode, sha))
        return out

    def to_push(self, head, base):
        """The commits reachable from `head` and not from `base` (None: every commit reachable from `head`), newest first."""
        known = set()
        if base:
            todo = [base]
            while todo:
                sha = todo.pop()
                if sha in known:
                    continue
                known.add(sha)
                todo.extend(self.commit(sha)[1])
        out, seen, todo = [], set(), [head] if head else []
        while todo:
            sha = todo.pop(0)
            if sha in seen or sha in known:
                continue
            seen.add(sha)
            out.append(sha)
            todo.extend(self.commit(sha)[1])
        return out

class Pack(object):
    def __init__(self, stem, fs=DISK):
        self.stem = stem
        self.fs = fs
        self.idx = fs.read(stem + ".idx")
        if self.idx[:4] != b"\xfftOc" or struct.unpack(">I", self.idx[4:8])[0] != 2:
            raise Unreadable("a pack index of a version this reader does not know")
        self.count = struct.unpack(">I", self.idx[8 + 255 * 4:8 + 256 * 4])[0]
        self.data = None

    def offset_of(self, sha):
        want = bytes.fromhex(sha)
        first = want[0]
        low = struct.unpack(">I", self.idx[8 + (first - 1) * 4:8 + first * 4])[0] if first else 0
        high = struct.unpack(">I", self.idx[8 + first * 4:8 + (first + 1) * 4])[0]
        names = 8 + 256 * 4
        while low < high:
            mid = (low + high) // 2
            name = self.idx[names + mid * 20:names + mid * 20 + 20]
            if name == want:
                offsets = names + self.count * 20 + self.count * 4
                value = struct.unpack(">I", self.idx[offsets + mid * 4:offsets + mid * 4 + 4])[0]
                if value & 0x80000000:
                    large = offsets + self.count * 4 + (value & 0x7FFFFFFF) * 8
                    value = struct.unpack(">Q", self.idx[large:large + 8])[0]
                return value
            if name < want:
                low = mid + 1
            else:
                high = mid
        return None

    def _bytes(self):
        if self.data is None:
            self.data = self.fs.read(self.stem + ".pack")
        return self.data

    def object_at(self, offset, repo):
        data = self._bytes()
        start = offset
        byte = data[offset]
        kind = (byte >> 4) & 7
        size = byte & 15
        shift = 4
        offset += 1
        while byte & 0x80:
            byte = data[offset]
            size |= (byte & 0x7F) << shift
            shift += 7
            offset += 1
        if kind in _TYPES:
            return _TYPES[kind], _inflate(data, offset, size)
        if kind == 6:                                     # a delta against an object earlier in this pack
            byte = data[offset]
            back = byte & 0x7F
            offset += 1
            while byte & 0x80:
                byte = data[offset]
                back = ((back + 1) << 7) | (byte & 0x7F)
                offset += 1
            base_kind, base = self.object_at(start - back, repo)
            return base_kind, _apply(base, _inflate(data, offset, size))
        if kind == 7:                                     # a delta against an object named by its id
            base_kind, base = repo.read(data[offset:offset + 20].hex())
            return base_kind, _apply(base, _inflate(data, offset + 20, size))
        raise Unreadable("a pack entry of a kind this reader does not know")


def _inflate(data, offset, size):
    out = zlib.decompressobj().decompress(data[offset:offset + size + 4096 + size // 2 + 64])
    if len(out) != size:
        out = zlib.decompressobj().decompress(data[offset:])
    if len(out) != size:
        raise Unreadable("a pack entry of the wrong size")
    return out


def _varint(delta, at):
    value, shift = 0, 0
    while True:
        byte = delta[at]
        at += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, at


def _apply(base, delta):
    size, at = _varint(delta, 0)
    if size != len(base):
        raise Unreadable("a delta against a base of the wrong size")
    target, at = _varint(delta, at)
    out = bytearray()
    while at < len(delta):
        op = delta[at]
        at += 1
        if op & 0x80:
            offset = length = 0
            for bit in range(4):
                if op & (1 << bit):
                    offset |= delta[at] << (8 * bit)
                    at += 1
            for bit in range(3):
                if op & (1 << (4 + bit)):
                    length |= delta[at] << (8 * bit)
                    at += 1
            out += base[offset:offset + (length or 0x10000)]
        elif op:
            out += delta[at:at + op]
            at += op
        else:
            raise Unreadable("a delta with a zero instruction")
    if len(out) != target:
        raise Unreadable("a delta that gives the wrong size")
    return bytes(out)


def blob_id(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def commit_holding(folder, files):
    """The commit of the nearest repository at or above `folder` where that commit holds every one of `files` (paths
    relative to `folder`, read from disk) at its path with the same bytes; None otherwise. Never raises."""
    try:
        found = nearest(folder)
        if found is None:
            return None
        top, gitdir = found
        repo = Repository(top, gitdir)
        commit = repo.head()
        if commit is None:
            return None
        rel = os.path.relpath(os.path.abspath(folder), os.path.abspath(top))
        prefix = [] if rel == "." else rel.split(os.sep)
        trees = {}

        def tree_at(parts):
            key = tuple(parts)
            if key not in trees:
                if not parts:
                    trees[key] = repo.entries(repo.tree_of_commit(commit))
                else:
                    parent = tree_at(parts[:-1])
                    if parent is None or parts[-1] not in parent or parent[parts[-1]][0] != "40000":
                        trees[key] = None
                    else:
                        trees[key] = repo.entries(parent[parts[-1]][1])
            return trees[key]

        for name in files:
            parts = prefix + name.split("/")
            tree = tree_at(parts[:-1])
            if tree is None or parts[-1] not in tree or tree[parts[-1]][0] not in ("100644", "100755"):
                return None
            with open(os.path.join(folder, *name.split("/")), "rb") as fh:
                if blob_id(fh.read()) != tree[parts[-1]][1]:
                    return None
        return commit if files else None
    except (Unreadable, OSError, ValueError, IndexError, struct.error, zlib.error, UnicodeDecodeError):
        return None
