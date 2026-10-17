"""The channels a secret is read from (the frame's SEC-2).

The hosting token is read in-process by one function, `read_tokens`: from the environment variable
its provider's declaration names, else from the hosting tool's own credentials file opened
read-only. It goes into the register and nowhere else. A database's connection address is read from
a file already on this machine, by `read_connection`, and is a secret whole.
"""
import json
import os
import urllib.parse


def read_tokens(world, facts, providers, register):
    """Every provider's token the declarations name, read into the register. Returns {provider: token}."""
    found = {}
    for name in sorted(providers):
        spec = providers[name].get("token")
        if not isinstance(spec, dict):
            continue
        token = world.env.get(spec.get("env") or "") or None
        if not token and isinstance(spec.get("credentials"), dict):
            location = facts.locations(world.fs).get(spec["credentials"].get("location") or "")
            if location:
                try:
                    doc = json.loads(world.fs.read_text(location))
                    token = doc.get(spec["credentials"].get("field") or "token") if isinstance(doc, dict) else None
                except (OSError, ValueError):
                    token = None
        if isinstance(token, str) and token:
            register.add(token, (), None, "channel")
            found[name] = token
    return found


def address_components(address):
    """What the register holds of a connection address beside the whole (SEC-12): the password, and
    the user and password pair."""
    try:
        parts = urllib.parse.urlsplit(address)
        user, password = parts.username, parts.password
    except ValueError:
        return []
    out = []
    if password:
        out.append(password)
        if user:
            out.append("%s:%s" % (user, password))
    return out


def read_connection(world, path, key_names):
    """The connection address a file on this machine holds under one of `key_names`, in-process.
    None where the file is not there or holds none."""
    try:
        text = world.fs.read_text(path)
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in key_names:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value or None
    return None
