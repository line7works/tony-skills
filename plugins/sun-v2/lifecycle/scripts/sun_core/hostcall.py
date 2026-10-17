"""The frame's own request to a provider's fixed host (the frame's SEC-2).

The hosting token is used "only in requests the frame itself makes to the provider's fixed host, over TLS, following no
redirect and logging no request, and is then dropped". A held value "goes back to the provider that issued it in such a
request of the frame's own, to that provider's fixed host and to no other" (which provider issued a held value is settled
when the rows are admitted, `rows._command_findings`).

A request is a declared command whose declaration says `"via": "request"`: its `method`, and its `template`, the parts of
the request's path, each a literal or a value of the row; and, where it declares them, its `query`, name and value pairs, and
its `body`, a JSON object whose leaves are such values, sent as `application/json` (G20-2). The host is the provider module's own `host` and no other. The
answer is handed to SEC-4's parser as a program's is: its status in place of an exit number, its body in place of standard
output, up to the same fixed size; a status the declaration's `exits` do not list is `other`. A redirect is an answer like
any other: it is not followed. Nothing of the request is logged, and the token is in no record: the transport is handed
it in the authorization header of the one request, and the header is dropped when the request ends.
"""
import http.client
import json
import socket
import ssl
import urllib.parse

from . import results

MOST_BODY = 1024 * 1024


class Refused(RuntimeError):
    """The request cannot be made as declared. `reason` is the tool's own fixed word."""

    def __init__(self, reason):
        RuntimeError.__init__(self, reason)
        self.reason = reason


class TLS(object):
    """The real transport: one HTTPS request to the host, with the system's default certificate checks; `http.client` follows
    no redirect, and nothing here logs."""

    def request(self, host, method, path, headers, timeout, body=None):
        connection = http.client.HTTPSConnection(host, 443, timeout=timeout, context=ssl.create_default_context())
        try:
            if body is None:
                connection.request(method, path, headers=headers)
            else:
                connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read(MOST_BODY + 1)
        finally:
            connection.close()


def path_of(parts):
    """The request's path from its parts, each percent-encoded whole."""
    return "/" + "/".join(urllib.parse.quote(str(part), safe="") for part in parts)


def leaves(node):
    """Every leaf of a JSON body, in order."""
    if isinstance(node, dict):
        return [leaf for value in node.values() for leaf in leaves(value)]
    if isinstance(node, list):
        return [leaf for value in node for leaf in leaves(value)]
    return [node]


def send(world, register, provider, declaration, parts, token, query=None, body=None):
    """Make the one request and return `results.Raw`. Raises `Refused` before the request where it cannot be made. `query`
    is its name and value pairs, `body` its JSON object, each value already filled from the row (G20-2)."""
    host = provider.get("host") if isinstance(provider, dict) else None
    if not isinstance(host, str) or not host:
        raise Refused("no host")
    path = path_of(parts)
    if query:
        path += "?" + urllib.parse.urlencode([(str(k), str(v)) for k, v in query])
    data = json.dumps(body, sort_keys=True).encode("utf-8") if body is not None else None
    # every part of the request but the authorization header is passed against the register (SEC-12): a value that holds
    # an entry goes no further
    texts = [str(part) for part in parts] + [path] + [str(v) for _k, v in query or []] + [str(v) for v in leaves(body)]
    if body is not None:
        texts.append(data.decode("utf-8"))
    if any(register.holds(text) for text in texts):
        raise Refused("register entry")
    method = str(declaration.get("method") or "GET")
    headers = {"Authorization": "Bearer " + token} if token else {}
    if data is not None:
        headers["Content-Type"] = "application/json"
    transport = world.transport if world.transport is not None else TLS()
    world.note("pre", "request", host)
    try:
        timeout = float(declaration.get("time_limit") or 60)
        if data is None:
            status, body = transport.request(host, method, path, headers, timeout)
        else:
            status, body = transport.request(host, method, path, headers, timeout, body=data)
    except socket.timeout:
        return results.Raw(None, b"", timed_out=True)
    except (OSError, http.client.HTTPException, ValueError):
        return results.Raw(None, b"", killed=True)
    finally:
        headers = None          # the token is dropped with the request
        world.note("post", "request", host)
    if not isinstance(status, int):
        return results.Raw(None, b"", killed=True)
    if len(body or b"") > MOST_BODY:
        return results.Raw(status, b"", oversize=True)
    return results.Raw(status, body or b"")
