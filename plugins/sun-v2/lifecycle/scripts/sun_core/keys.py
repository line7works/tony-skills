"""Project keys and their fingerprints (the frame's RUN-2).

A key is the project's name folded: lowercased, with every character that is not a letter or a digit
removed. A key is written nowhere as it is. What is written of one is its fingerprint: HMAC-SHA256
under the keying value, a random value the tool makes once on a machine and keeps in an owner-only
file of its own beside the run directories.
"""
import hashlib
import hmac

from . import fsio


def fold(name):
    return "".join(ch for ch in name.lower() if ch.isalnum())


def fingerprint(keying_value, key):
    return hmac.new(keying_value.encode("ascii"), key.encode("utf-8"), hashlib.sha256).hexdigest()


def keying_state(fs, facts):
    """`ok`, `missing` or `wide`, with nothing read of the file but its presence and its mode."""
    if not fs.lexists(facts.keying_file):
        return "missing"
    if fs.mode(facts.keying_file) & 0o077 or fs.islink(facts.keying_file):
        return "wide"
    return "ok"


def read_keying(fs, facts):
    return fs.read_text(facts.keying_file).strip()


def make_keying(world, facts):
    """Made once on a machine, by a create that fails if another invocation made it first; the
    loser of that race reads the winner's value."""
    fs = world.fs
    fs.makedirs(facts.tool_home)
    try:
        fs.write_new(facts.keying_file, (world.random_hex(32) + "\n").encode("ascii"))
    except fsio.Exists:
        pass
    return read_keying(fs, facts)
