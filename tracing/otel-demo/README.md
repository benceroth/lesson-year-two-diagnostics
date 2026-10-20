# Tracing demo (four services, one trace)

Verified path (no Docker, stdlib only):

```bash
python tracing/otel-demo/run_demo.py
```

This starts Billing, Identity, Reporting and Notifications as tiny HTTP services in one process,
sends six concurrent invoice requests, and renders a request-wide breakdown twice: without and with
W3C `traceparent` propagation. Without it, 90% of the slowest request is one opaque client call.
With it, the same time resolves to a `queue.wait` inside Reporting - the queue the post warns about.

Run services separately (four terminals, `TRACE_FILE=spans.jsonl`):

```bash
python tracing/otel-demo/services.py reporting --port 8103   # and identity 8102, notifications 8104, billing 8101
curl -X POST http://127.0.0.1:8101/invoices
python tracing/render_breakdown.py spans.jsonl
```

Files: `tracelib.py` (traceparent + JSONL span writer), `services.py`, `run_demo.py`.

## Honest limits

- This is **not** the OpenTelemetry SDK. It uses the same wire format (W3C Trace Context) and a similar
  span shape so you can see the idea with zero installs. In production use an OpenTelemetry SDK/auto-instrumentation.
- Sleeps simulate work; timings are real wall-clock measurements on your machine and vary run to run.
- `docker-compose.yml` and `otel-collector.yaml` are **unverified extras** (written without Docker).
  The collector only tails the JSONL as logs; it does not turn it into OTLP traces.
