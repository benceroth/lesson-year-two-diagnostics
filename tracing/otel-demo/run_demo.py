"""Start the four services in one process, fire concurrent invoice requests, render breakdowns.

    python tracing/otel-demo/run_demo.py            # runs WITHOUT and WITH trace propagation
    python tracing/otel-demo/run_demo.py --out-dir tracing/sample-output

Timings are real wall-clock measurements from your machine (sleeps simulate work), so
numbers vary slightly between runs; the *shape* (a long queue wait that only appears
with propagation) is stable.
"""

import argparse
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from render_breakdown import analyze, load_spans, render  # noqa: E402
from services import SERVICES, make_server  # noqa: E402
from tracelib import SpanWriter  # noqa: E402


def run(propagate, trace_file, requests=6, concurrency=6, export_ms=80):
    trace_file = Path(trace_file)
    trace_file.write_text("", encoding="utf-8")
    writer, urls = SpanWriter(str(trace_file)), {}
    servers = {s: make_server(s, 0, urls, writer, propagate, export_ms) for s in SERVICES}
    for s, srv in servers.items():
        urls[s] = f"http://127.0.0.1:{srv.server_address[1]}"
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        def call(_):
            req = urllib.request.Request(urls["billing"] + "/invoices", method="POST", data=b"{}")
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            statuses = list(pool.map(call, range(requests)))
        assert all(s == 201 for s in statuses), statuses
    finally:
        for srv in servers.values():
            srv.shutdown()
            srv.server_close()
    return trace_file


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(HERE.parent / "sample-output"))
    ap.add_argument("--requests", type=int, default=6)
    ap.add_argument("--concurrency", type=int, default=6)
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    parts = ["# Request-wide breakdown (measured on one local run)", "",
             "Numbers are wall-clock timings from this run, not benchmarks. "
             f"{args.requests} concurrent invoice requests share one single-worker export queue in Reporting.", ""]
    for propagate, label, fname in ((False, "WITHOUT trace-context propagation", "spans-no-propagation.jsonl"),
                                    (True, "WITH W3C traceparent propagation", "spans-propagated.jsonl")):
        path = run(propagate, out_dir / fname, args.requests, args.concurrency)
        parts.append(render(analyze(load_spans(path)), label))
    text = "\n".join(parts)
    (out_dir / "breakdown.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
