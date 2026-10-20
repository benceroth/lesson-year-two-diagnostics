"""Render a request-wide latency/wait breakdown from a spans JSONL file.

    python tracing/render_breakdown.py spans.jsonl [--out breakdown.md]

Categories (per span *self* time, i.e. minus time covered by child spans):
  work                         server/internal spans doing something
  wait (queue/backoff)         spans marked wait=true (queue.wait, retry backoff)
  network + unattributed       client span time not covered by the remote server span
  opaque wait (no remote spans) client span with NO child: the callee is invisible
"""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

CATEGORIES = ("work", "wait (queue/backoff)", "network + unattributed", "opaque wait (no remote spans)")
ROOT_NAME = "POST /invoices"


def load_spans(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _ms(ns):
    return ns / 1e6


def _union_ns(intervals, lo, hi):
    total, cur_end = 0, lo
    for s, e in sorted((max(s, lo), min(e, hi)) for s, e in intervals if e > lo and s < hi):
        s = max(s, cur_end)
        if e > s:
            total += e - s
            cur_end = e
    return total


def analyze(spans):
    by_trace = defaultdict(list)
    for s in spans:
        by_trace[s["trace_id"]].append(s)
    requests, orphan_spans = [], 0
    for tid, group in sorted(by_trace.items()):
        roots = [s for s in group if s["name"] == ROOT_NAME and s["service"] == "billing" and s["kind"] == "server"]
        if not roots:
            orphan_spans += len(group)
            continue
        children = defaultdict(list)
        for s in group:
            children[s["parent_span_id"]].append(s)
        root = roots[0]
        cells = defaultdict(float)
        for s in group:
            kids = children.get(s["span_id"], [])
            self_ns = (s["end_ns"] - s["start_ns"]) - _union_ns(
                [(k["start_ns"], k["end_ns"]) for k in kids], s["start_ns"], s["end_ns"])
            if s["attributes"].get("wait"):
                cat = "wait (queue/backoff)"
            elif s["kind"] == "client":
                cat = "network + unattributed" if kids else "opaque wait (no remote spans)"
            else:
                cat = "work"
            cells[(s["service"], cat)] += _ms(max(self_ns, 0))
        requests.append({
            "trace_id": tid, "total_ms": _ms(root["end_ns"] - root["start_ns"]),
            "cells": dict(cells), "tree": _tree(root, children),
            "services_seen": sorted({s["service"] for s in group}),
            "wait_ms": sum(v for (_, c), v in cells.items() if c.startswith("wait")),
            "opaque_ms": sum(v for (_, c), v in cells.items() if c.startswith("opaque")),
        })
    requests.sort(key=lambda r: (-r["total_ms"], r["trace_id"]))
    return {"requests": requests, "orphan_spans": orphan_spans}


def _tree(span, children, depth=0):
    lines = [(depth, span["service"], span["name"], _ms(span["end_ns"] - span["start_ns"]),
              bool(span["attributes"].get("wait")))]
    for kid in sorted(children.get(span["span_id"], []), key=lambda k: k["start_ns"]):
        lines += _tree(kid, children, depth + 1)
    return lines


def render(analysis, title="Request-wide breakdown"):
    reqs = analysis["requests"]
    out = [f"## {title}", ""]
    if not reqs:
        return "\n".join(out + ["No request traces found.", ""])
    totals = [r["total_ms"] for r in reqs]
    out += [
        f"Requests: {len(reqs)} | median {statistics.median(totals):.0f} ms | max {max(totals):.0f} ms | "
        f"spans in traces that never join a request: {analysis['orphan_spans']}",
        "",
        "| Request (slowest first) | Total ms | Wait ms (queue/backoff) | Opaque wait ms | Services visible |",
        "|---|---|---|---|---|",
    ]
    for i, r in enumerate(reqs, 1):
        out.append(f"| #{i} | {r['total_ms']:.0f} | {r['wait_ms']:.0f} | {r['opaque_ms']:.0f} | {', '.join(r['services_seen'])} |")
    worst = reqs[0]
    out += ["", f"### Slowest request ({worst['total_ms']:.0f} ms)", "", "```text"]
    for depth, svc, name, ms, wait in worst["tree"]:
        out.append(f"{'  ' * depth}{svc}: {name}  {ms:.0f} ms{'   <-- WAIT' if wait else ''}")
    out += ["```", "", "| Service | Category | ms | % of request | |", "|---|---|---|---|---|"]
    for (svc, cat), ms in sorted(worst["cells"].items(), key=lambda kv: -kv[1]):
        if ms < 0.5:
            continue
        pct = ms / worst["total_ms"] * 100
        out.append(f"| {svc} | {cat} | {ms:.0f} | {pct:.0f}% | {'#' * max(1, round(pct / 4))} |")
    out.append("")
    if worst["opaque_ms"] > 0 and "reporting" not in worst["services_seen"]:
        out += [f"> {worst['opaque_ms']:.0f} ms of this request is spent waiting on services that emitted no spans "
                "into this trace. Without shared trace context the cause is invisible.", ""]
    elif worst["wait_ms"] > 0:
        out += [f"> {worst['wait_ms']:.0f} ms is queue/backoff wait - time no service would call 'work' and no CPU chart shows.", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("spans")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    text = render(analyze(load_spans(args.spans)))
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
