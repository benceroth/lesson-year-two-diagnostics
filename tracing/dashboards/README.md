# Dashboards: panels to build from spans

`render_breakdown.py` computes these from `spans.jsonl`. In a real tracing backend, build the same panels:

| Panel | Query idea | Why |
|---|---|---|
| Request P50/P95 latency | duration of root server span `POST /invoices` | the user-facing symptom |
| Latency by service and category | span self time grouped by service and `wait` attribute | shows work vs. wait |
| Queue / wait time | spans with `wait=true` (`queue.wait`, backoff) | the hidden queue |
| Opaque client time | client spans with no child span | a callee that does not propagate context |
| Error rate | root spans with `error=true` | pair with latency |
| Deployment markers | annotate deploys on every panel | connect behavior changes to releases |

Targets in the post (P95 <= 350 ms) are the fictional product's goals, not standards.
