"""Four tiny HarborLedger services (billing, identity, reporting, notifications).

Each service writes spans to a shared JSONL file and propagates W3C `traceparent`.
Set propagate=False (or PROPAGATE=0) to see what responders see *without* shared context.

Run one service:  python services.py billing --port 8101
(or use run_demo.py, which starts all four in one process)
"""

import argparse
import json
import os
import queue
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tracelib import (Span, SpanWriter, default_trace_file, format_traceparent,
                      new_trace_id, parse_traceparent)

SERVICES = ("billing", "identity", "reporting", "notifications")
DEFAULT_PORTS = {"billing": 8101, "identity": 8102, "reporting": 8103, "notifications": 8104}


class ServiceState:
    def __init__(self, name, writer, urls, propagate=True, export_ms=80):
        self.name, self.writer, self.urls = name, writer, urls
        self.propagate, self.export_ms = propagate, export_ms
        self.jobs = queue.Queue()  # reporting: single-worker queue = the hidden wait
        self.failed_once = set()
        self.lock = threading.Lock()


def _sleep_span(state, ctx, name, seconds, wait=False):
    with Span(state.writer, state.name, name, ctx[0], ctx[1], "internal", {"wait": wait} if wait else {}):
        time.sleep(seconds)


def _call(state, ctx, target, method, path, request_id):
    """Outgoing HTTP call wrapped in a client span; injects traceparent when propagating."""
    with Span(state.writer, state.name, f"HTTP {method} {target}{path}", ctx[0], ctx[1], "client") as client:
        headers = {"X-Request-Id": request_id}
        if state.propagate:
            headers["traceparent"] = format_traceparent(ctx[0], client.span_id)
        req = urllib.request.Request(state.urls[target] + path, method=method, headers=headers,
                                     data=b"{}" if method == "POST" else None)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
                client.attributes["http.status_code"] = resp.status
                return resp.status
        except urllib.error.HTTPError as exc:
            client.attributes["http.status_code"] = exc.code
            exc.read()
            exc.close()
            return exc.code


def handle(state, method, path, headers):
    """Returns (status, body). Creates the server span; internal work happens beneath it."""
    parsed = parse_traceparent(headers.get("traceparent")) if state.propagate else None
    trace_id, parent = parsed if parsed else (new_trace_id(), None)
    request_id = headers.get("X-Request-Id") or new_trace_id()[:8]
    with Span(state.writer, state.name, f"{method} {path}", trace_id, parent, "server") as server:
        ctx = (trace_id, server.span_id)
        route = (state.name, method, path)

        if route == ("billing", "POST", "/invoices"):
            if _call(state, ctx, "identity", "GET", "/authorize", request_id) != 200:
                return 403, {"error": "forbidden"}
            _sleep_span(state, ctx, "invoice.compute", 0.03)
            _call(state, ctx, "reporting", "POST", "/exports", request_id)  # synchronous: on the critical path
            for attempt in range(3):
                if _call(state, ctx, "notifications", "POST", "/notify", request_id) == 200:
                    break
                server.attributes["notify.retries"] = attempt + 1
                _sleep_span(state, ctx, "notify.retry_backoff", 0.03, wait=True)
            return 201, {"invoice": "created"}

        if route == ("identity", "GET", "/authorize"):
            _sleep_span(state, ctx, "authz.check", 0.02)
            return 200, {"allowed": True}

        if route == ("reporting", "POST", "/exports"):
            done = threading.Event()
            state.jobs.put((ctx, time.time_ns(), done))
            done.wait()
            return 200, {"export": "built"}

        if route == ("notifications", "POST", "/notify"):
            with state.lock:
                first = request_id not in state.failed_once
                state.failed_once.add(request_id)
            if first:
                server.attributes["error"] = True
                return 503, {"error": "transient"}  # deterministic first-attempt failure
            _sleep_span(state, ctx, "notify.send", 0.05)
            return 200, {"sent": True}

    return 404, {"error": "not found"}


def _reporting_worker(state):
    while True:
        ctx, enqueued_ns, done = state.jobs.get()
        with Span(state.writer, state.name, "queue.wait", ctx[0], ctx[1], "internal", {"wait": True}) as wait_span:
            wait_span.start_ns = enqueued_ns  # time spent behind other exports
        _sleep_span(state, ctx, "export.build", state.export_ms / 1000)
        done.set()


def make_server(name, port, urls, writer, propagate=True, export_ms=80, host="127.0.0.1"):
    state = ServiceState(name, writer, urls, propagate, export_ms)

    class Handler(BaseHTTPRequestHandler):
        def _serve(self):
            status, body = handle(state, self.command, self.path, self.headers)
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = _serve

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.state = state
    if name == "reporting":
        threading.Thread(target=_reporting_worker, args=(state,), daemon=True).start()
    return server


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("service", choices=SERVICES)
    ap.add_argument("--port", type=int)
    args = ap.parse_args(argv)
    urls = {s: os.environ.get(f"{s.upper()}_URL", f"http://127.0.0.1:{DEFAULT_PORTS[s]}") for s in SERVICES}
    server = make_server(
        args.service, args.port or DEFAULT_PORTS[args.service], urls, SpanWriter(default_trace_file()),
        propagate=os.environ.get("PROPAGATE", "1") != "0",
        export_ms=int(os.environ.get("EXPORT_MS", "80")),
        host="0.0.0.0" if os.environ.get("BIND_ALL") else "127.0.0.1",
    )
    print(f"{args.service} listening on {server.server_address}")
    server.serve_forever()


if __name__ == "__main__":
    main()
