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
        plain = urllib.parse.unquote(password)
        if plain != password:               # the password as the dump tool reads it from the service file (G20-1)
            out.append(plain)
    return out


def service_file(address, service):
    """The whole connection address as one libpq service section (G20-1; SEC-2): `[service]`, then host, port, dbname, user
    and password, then each of the address's parameters, one `key=value` line each, the URI's percent-encoding read off.
    A service file has no escape: a part that cannot be one such line (a line break or another character of Part 2's core in
    it, white space at either end of a part, `=` in a parameter's name, or several hosts) cannot be written, and raises
    ValueError (GOV-1; the control room's reading, A153). Each part is checked on its own, so white space at an end of a value
    is found though its line begins with the key (G22-6)."""
    from . import chars
    unquote = urllib.parse.unquote
    try:
        parts = urllib.parse.urlsplit(address)
        port = parts.port
        user, _, hostport = parts.netloc.rpartition("@")
        host = hostport.rpartition(":")[0] if port is not None else hostport
        params = urllib.parse.parse_qsl(parts.query, keep_blank_values=True, strict_parsing=bool(parts.query))
    except ValueError:
        raise ValueError("not an address")
    if parts.scheme not in ("postgres", "postgresql") or parts.fragment:
        raise ValueError("not an address")
    found = [("host", unquote(host)), ("port", str(port) if port is not None else ""),
             ("dbname", unquote(parts.path[1:]) if parts.path.startswith("/") else ""),
             ("user", unquote(parts.username or "")), ("password", unquote(parts.password or ""))]
    if "," in found[0][1]:
        raise ValueError("several hosts")             # a service section names one host
    pairs = [(k, v) for k, v in found if v]
    for key, value in params:
        if not key or "=" in key:
            raise ValueError("a parameter's name")
        pairs.append((key, value))
    for part in [service] + [p for pair in pairs for p in pair]:
        if any(chars.in_core(ch) for ch in part) or part != part.strip():
            raise ValueError("a part that cannot be one line")
    return ("\n".join(["[%s]" % service] + ["%s=%s" % pair for pair in pairs]) + "\n").encode("utf-8")


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
