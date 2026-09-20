#!/usr/bin/env python3
"""The wall's one hole: a filtering CONNECT proxy on loopback (sealed bench, A2).

The sandbox profile denies every network operation except one loopback port. The runner
starts this proxy OUTSIDE the wall on that port before a launch and stops it after, so a
session command cannot reach GitHub, the public answer key or any service; what speaks to the
proxy reaches only the hosts the setup declared.

Policy, and nothing else:

- `CONNECT host:port` is allowed only when `host` matches the setup's allowlist and the port
  is one the allowlist entry names (443 unless the entry says otherwise). Everything else is
  refused with `403`.
- A plain HTTP request (an absolute-URI `GET`, `POST`, anything that is not `CONNECT`) is
  refused with `403`. The proxy never fetches anything itself.
- Every request is one JSON line in the log: the time, the host, the port, allowed or refused,
  and the bytes each way. NEVER a header and never a body — the tunnel's bytes are counted,
  not read, and TLS makes them opaque in any case.

Python 3.9, standard library only. Run it standalone for a test:

    wall_proxy.py --allow api.anthropic.com --allow 127.0.0.1:8123 --log <file> [--port 0]

which prints one JSON line naming the port it bound and then serves until it is killed.
"""
import argparse
import errno
import json
import os
import select
import socket
import socketserver
import sys
import threading
import time

BUFFER = 65536
IDLE_SECONDS = 900
# How much of one direction the proxy will hold in memory before it stops READING that
# direction. This is how back-pressure is passed along: a slow far side fills its own kernel
# buffer, the relay's buffer then fills, and the relay stops reading from the fast side, which
# fills ITS kernel buffer and slows the sender down. Nothing is dropped and nothing grows
# without bound.
HIGH_WATER = 1 << 20


def parse_allow(entries):
    """`[(host, port)]` from `host` or `host:port` strings; a bare host means 443."""
    rows = []
    for entry in entries or []:
        text = entry.strip()
        if not text:
            continue
        if ":" in text:
            host, _, port = text.rpartition(":")
            try:
                rows.append((host.lower(), int(port)))
            except ValueError:
                raise ValueError("%r is not host or host:port" % entry)
        else:
            rows.append((text.lower(), 443))
    return rows


def allowed(rows, host, port):
    """Is this exact host allowed on this port? An entry matches the host itself and its
    subdomains, so `anthropic.com` would cover `api.anthropic.com` — which is why the
    setups' lists name full hostnames rather than parent domains."""
    host = (host or "").lower().rstrip(".")
    for entry_host, entry_port in rows:
        if port != entry_port:
            continue
        if host == entry_host or host.endswith("." + entry_host):
            return True
    return False


# EAGAIN and EWOULDBLOCK are the same errno on macOS, and `BlockingIOError` covers both;
# `InterruptedError` is EINTR. None of the three means the peer went away, and treating any of
# them as a close is what dropped a live session mid-stream.
def _recv(sock):
    """`(blob, closed, fatal)`. `closed` is a real EOF; `fatal` is a real error."""
    try:
        blob = sock.recv(BUFFER)
    except (BlockingIOError, InterruptedError):
        return b"", False, None
    except (socket.error, OSError) as exc:
        if exc.errno in _RETRY:
            return b"", False, None
        if exc.errno in (errno.ECONNRESET, errno.EPIPE):
            return b"", True, None
        return b"", True, "recv failed: %s" % exc
    if not blob:
        return b"", True, None
    return blob, False, None


def _send(sock, blob):
    """`(bytes actually sent, fatal)`. A partial send is normal and is carried over."""
    try:
        return sock.send(blob), None
    except (BlockingIOError, InterruptedError):
        return 0, None
    except (socket.error, OSError) as exc:
        if exc.errno in _RETRY:
            return 0, None
        return 0, "send failed: %s" % exc


_RETRY = frozenset(e for e in (getattr(errno, "EAGAIN", None),
                               getattr(errno, "EWOULDBLOCK", None),
                               getattr(errno, "EINTR", None)) if e is not None)


class _Handler(socketserver.StreamRequestHandler):
    timeout = 60
    # UNBUFFERED. `readline` on a buffered `rfile` reads ahead, so bytes the client sent
    # immediately after the CONNECT headers — a TLS ClientHello in the same packet — would sit
    # in a Python buffer that the byte relay below never looks at, and the session would hang
    # or fail its handshake. Reading the request line and the headers one byte at a time costs
    # nothing next to a TLS session and leaves the socket exactly where the relay expects it.
    rbufsize = 0

    def log_line(self, document):
        self.server.log(document)

    def refuse(self, why, host=None, port=None, method=None):
        self.log_line({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "host": host, "port": port, "method": method,
                       "outcome": "refused", "why": why,
                       "bytes_to_host": 0, "bytes_to_client": 0})
        try:
            self.wfile.write(("HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n"
                              "Connection: close\r\n\r\n").encode("ascii"))
            self.wfile.flush()
        except (IOError, OSError):
            pass

    def handle(self):
        try:
            line = self.rfile.readline(8192)
        except (IOError, OSError):
            return
        if not line:
            return
        parts = line.decode("latin-1").strip().split()
        if len(parts) < 2:
            return self.refuse("the request line is not a request line")
        method, target = parts[0].upper(), parts[1]
        # drain the headers; they are read off the socket and never recorded
        while True:
            try:
                header = self.rfile.readline(8192)
            except (IOError, OSError):
                return
            if not header or header in (b"\r\n", b"\n"):
                break
        if method != "CONNECT":
            return self.refuse("only CONNECT is proxied; a plain HTTP request is refused",
                               method=method)
        host, _, port_text = target.rpartition(":")
        if not host:
            return self.refuse("CONNECT names no host:port", method=method)
        try:
            port = int(port_text)
        except ValueError:
            return self.refuse("CONNECT names no port", host=host, method=method)
        if not allowed(self.server.allow_rows, host, port):
            return self.refuse("not on this setup's allowlist", host=host, port=port,
                               method=method)
        try:
            upstream = socket.create_connection((host, port), timeout=30)
        except (socket.error, OSError) as exc:
            return self.refuse("the host did not connect: %s" % exc, host=host, port=port,
                               method=method)
        try:
            self.wfile.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
            self.wfile.flush()
        except (IOError, OSError):
            upstream.close()
            return
        to_host, to_client, broken = self.pump(upstream)
        self.log_line({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "host": host, "port": port, "method": "CONNECT",
                       "outcome": "allowed", "why": "on this setup's allowlist",
                       # A relay that ended on anything but a clean close says so, by name. A
                       # dropped stream used to be indistinguishable from a finished one.
                       "ended": broken or "both directions closed",
                       "clean": broken is None,
                       "bytes_to_host": to_host, "bytes_to_client": to_client})

    def pump(self, upstream):
        """Relay bytes both ways until BOTH directions have closed. Counted, never recorded.

        Back-pressure must never look like a closed connection. The first version set both
        sockets non-blocking and then called `sendall` on them: when the far side's send
        buffer filled — a large request body going up, or a long response streaming down —
        `sendall` raised `BlockingIOError` (EAGAIN), the handler treated it as a close, and
        the proxy tore the connection down mid-stream. Measured by the control room on
        2026-09-19 (proof root `wall-proof-20260919T162738Z`): two walled comparison trials
        ran for about three minutes and then ended `API Error: Connection dropped
        (ECONNRESET)`, with `bytes_to_host` at 131404 on one of them. The native probe never
        hit it because its exchange is small enough to fit in the buffers.

        So: `select` for readability AND for writability, one pending buffer per direction,
        partial sends carried over, and EAGAIN / EWOULDBLOCK / EINTR handled as "not yet",
        never as "closed". When one side sends EOF the relay flushes what it still holds,
        shuts down the WRITE half of the other side, and keeps relaying the opposite direction
        until it closes too, because a half-closed connection is a normal thing for a client
        to do and the other direction's data is still owed.
        """
        client = self.connection
        client.setblocking(False)
        upstream.setblocking(False)
        directions = [
            {"name": "to_host", "src": client, "dst": upstream},
            {"name": "to_client", "src": upstream, "dst": client},
        ]
        for side in directions:
            side.update({"buffer": b"", "src_eof": False, "dst_shut": False, "bytes": 0})
        broken = None
        try:
            while True:
                readers = [s["src"] for s in directions
                           if not s["src_eof"] and len(s["buffer"]) < HIGH_WATER]
                writers = [s["dst"] for s in directions if s["buffer"]]
                if not readers and not writers:
                    break
                try:
                    ready, writable, bad = select.select(readers, writers,
                                                         readers + writers, IDLE_SECONDS)
                except InterruptedError:
                    continue
                except (socket.error, OSError) as exc:
                    broken = "select failed: %s" % exc
                    break
                if bad:
                    broken = "a socket reported an error condition"
                    break
                if not ready and not writable:
                    broken = "idle for %d seconds" % IDLE_SECONDS
                    break
                for side in directions:
                    if side["src"] in ready:
                        blob, closed, fatal = _recv(side["src"])
                        if fatal:
                            broken = "%s: %s" % (side["name"], fatal)
                        if closed:
                            side["src_eof"] = True
                        elif blob:
                            side["buffer"] += blob
                    if side["buffer"] and side["dst"] in writable:
                        sent, fatal = _send(side["dst"], side["buffer"])
                        side["buffer"] = side["buffer"][sent:]
                        side["bytes"] += sent
                        if fatal:
                            broken = "%s: %s" % (side["name"], fatal)
                    # EOF travels only after everything already read has gone out.
                    if side["src_eof"] and not side["buffer"] and not side["dst_shut"]:
                        side["dst_shut"] = True
                        try:
                            side["dst"].shutdown(socket.SHUT_WR)
                        except (socket.error, OSError):
                            pass
                if broken:
                    break
                if all(s["dst_shut"] for s in directions):
                    break
        finally:
            try:
                client.setblocking(True)
            except (socket.error, OSError):
                pass
            try:
                upstream.close()
            except (socket.error, OSError):
                pass
        counts = {s["name"]: s["bytes"] for s in directions}
        return counts["to_host"], counts["to_client"], broken

    def log_message(self, *args):        # never the default stderr line
        pass


class WallProxy(socketserver.ThreadingTCPServer):
    """One proxy for one launch: `start()`, then `port`, then `stop()`."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, allow, log_path, host="127.0.0.1", port=0):
        self.allow_rows = parse_allow(allow)
        self.log_path = log_path
        self._log_lock = threading.Lock()
        self._thread = None
        socketserver.ThreadingTCPServer.__init__(self, (host, port), _Handler)

    @property
    def port(self):
        return self.server_address[1]

    def log(self, document):
        if not self.log_path:
            return
        directory = os.path.dirname(self.log_path)
        if directory and not os.path.isdir(directory):
            try:
                os.makedirs(directory)
            except OSError:
                pass
        with self._log_lock:
            try:
                with open(self.log_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(document, sort_keys=True) + "\n")
                    handle.flush()
            except (IOError, OSError):
                pass

    def start(self):
        self._thread = threading.Thread(target=self.serve_forever,
                                        kwargs={"poll_interval": 0.1})
        self._thread.daemon = True
        self._thread.start()
        return self.port

    def stop(self):
        try:
            self.shutdown()
        finally:
            self.server_close()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

    def handle_error(self, request, client_address):
        """A broken pipe from a client that walked away is not an event worth a traceback."""
        self.log({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "outcome": "error", "why": "the connection raised",
                  "host": None, "port": None,
                  "bytes_to_host": 0, "bytes_to_client": 0})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--allow", action="append", default=[],
                        help="an allowed `host` or `host:port`; repeatable")
    parser.add_argument("--log", required=True, help="the JSONL request log")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    proxy = WallProxy(args.allow, args.log, port=args.port)
    sys.stdout.write(json.dumps({"port": proxy.port, "allow": args.allow,
                                 "log": args.log}) + "\n")
    sys.stdout.flush()
    proxy.start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        proxy.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
