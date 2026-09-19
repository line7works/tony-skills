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


class _Handler(socketserver.StreamRequestHandler):
    timeout = 60

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
        to_host, to_client = self.pump(upstream)
        self.log_line({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "host": host, "port": port, "method": "CONNECT",
                       "outcome": "allowed", "why": "on this setup's allowlist",
                       "bytes_to_host": to_host, "bytes_to_client": to_client})

    def pump(self, upstream):
        """Bytes both ways until either side closes. Counted, never recorded."""
        client = self.connection
        client.setblocking(False)
        upstream.setblocking(False)
        to_host = to_client = 0
        try:
            while True:
                ready, _w, bad = select.select([client, upstream], [], [client, upstream],
                                               IDLE_SECONDS)
                if bad or not ready:
                    break
                closed = False
                for source in ready:
                    try:
                        blob = source.recv(BUFFER)
                    except (socket.error, OSError):
                        closed = True
                        break
                    if not blob:
                        closed = True
                        break
                    target = upstream if source is client else client
                    try:
                        target.sendall(blob)
                    except (socket.error, OSError):
                        closed = True
                        break
                    if source is client:
                        to_host += len(blob)
                    else:
                        to_client += len(blob)
                if closed:
                    break
        finally:
            try:
                upstream.close()
            except (socket.error, OSError):
                pass
        return to_host, to_client

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
