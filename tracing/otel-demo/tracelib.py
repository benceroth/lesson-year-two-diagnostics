"""W3C Trace Context (traceparent) helpers and a JSONL span writer. Stdlib only.

traceparent = 00-<32 hex trace id>-<16 hex parent span id>-<2 hex flags>
Spec: https://www.w3.org/TR/trace-context/
"""

import json
import os
import re
import secrets
import threading
import time

_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
_write_lock = threading.Lock()


def new_trace_id():
    return secrets.token_hex(16)


def new_span_id():
    return secrets.token_hex(8)


def format_traceparent(trace_id, span_id, flags="01"):
    return f"00-{trace_id}-{span_id}-{flags}"


def parse_traceparent(value):
    """Return (trace_id, parent_span_id) or None if missing/invalid/all-zero."""
    m = _TRACEPARENT.match((value or "").strip().lower())
    if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
        return None
    return m.group(1), m.group(2)


class SpanWriter:
    """Appends one JSON object per span to a file shared by all services."""

    def __init__(self, path):
        self.path = path

    def write(self, span):
        line = json.dumps(span, sort_keys=True) + "\n"
        with _write_lock, open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line)


class Span:
    def __init__(self, writer, service, name, trace_id, parent_id, kind, attributes=None):
        self.writer, self.service, self.name = writer, service, name
        self.trace_id, self.parent_id, self.kind = trace_id, parent_id, kind
        self.span_id = new_span_id()
        self.attributes = dict(attributes or {})
        self.start_ns = time.time_ns()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.attributes["error"] = True
        self.end()
        return False

    def end(self, start_ns=None, end_ns=None):
        self.writer.write({
            "trace_id": self.trace_id, "span_id": self.span_id, "parent_span_id": self.parent_id,
            "service": self.service, "name": self.name, "kind": self.kind,
            "start_ns": self.start_ns if start_ns is None else start_ns,
            "end_ns": time.time_ns() if end_ns is None else end_ns,
            "attributes": self.attributes,
        })


def default_trace_file():
    return os.environ.get("TRACE_FILE", "spans.jsonl")
