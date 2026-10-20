# lesson-year-two-diagnostics

[![ci](https://github.com/benceroth/lesson-year-two-diagnostics/actions/workflows/ci.yml/badge.svg)](https://github.com/benceroth/lesson-year-two-diagnostics/actions/workflows/ci.yml)

**The question:** is our year-two pain about infrastructure capacity, or about connections and team structure (Conway's Law)?
**After this you can:** run one command on your own repository and get evidence - change coupling, hotspots, ownership by team, a dependency map - then trace one request to find the wait nobody owns, and start a 90-day recovery plan.

Companion to *Why Scalable Architectures Fail in Year Two—and How to Adapt* (fictional product: HarborLedger). Story link: [read it on Medium](https://medium.com/@benceroth/why-scalable-architectures-fail-in-year-two-6de2be7f6202).

## Run it on your repository (one command)

Requires Python 3.10+ and git. No dependencies, no network.

```bash
python y2diag.py analyze /path/to/your/repo --config tool/config.example.yaml --since 2024-01-01
```

Output goes to `y2diag-report/`: `report.md`, `report.html`, `findings.json`, `dependencies.mmd`, `dependencies.dot`.
Copy `tool/config.example.yaml` to map teams to paths and authors to teams (CODEOWNERS is honoured when config has no rule). Use `--since`, `--paths`, `--max-commits` on large repositories.

## Demo first: see output on a synthetic history

```bash
python demo/make_sample_report.py          # builds a reproducible synthetic repo in a temp dir and re-creates demo/sample-report/
```

The committed [sample report](./demo/sample-report/report.md) ([HTML](./demo/sample-report/report.html)) was generated for real from that history. It plants:

| Planted pattern | What the report shows (measured on the sample) |
|---|---|
| `invoice.py` <-> `export.py` change together across teams | 30 co-changes, confidence 1.0 |
| Ownership bottleneck in `src/billing` | edited by 5 teams; the owner authors 35% of changes |
| Hotspot | `invoice.py`: churn 84 x complexity 95.9 |
| Billing <-> Reporting import cycle | mutual dependency in the map |
| A mass reformat touching 40+ files | ignored for coupling (noise) |

Tests assert the analyzers find each of these.

## Tracing demo: the hidden queue (no Docker)

```bash
python tracing/otel-demo/run_demo.py
```

Four tiny stdlib HTTP services (Billing, Identity, Reporting, Notifications) propagate W3C `traceparent` and write spans to JSONL. Six concurrent invoice requests share a single-worker export queue in Reporting. The renderer prints a request-wide breakdown twice - see [tracing/sample-output/breakdown.md](./tracing/sample-output/breakdown.md) (measured on one local run, timings vary):

- **Without propagation:** 581 ms of the slowest 646 ms request is one opaque call; nothing says why.
- **With propagation:** the same time resolves to `reporting: queue.wait 400 ms`.

That is the post's "dependencies become queues" claim, made visible. Docker Compose / collector files exist as **unverified** extras ([details](./tracing/otel-demo/README.md)).

## 90-day recovery

[recovery-plan/90-day-template.md](./recovery-plan/90-day-template.md) uses the post's ranges (Days 1-10, 11-30, 31-45, 46-75, 76-90), each with evidence checkpoints and exit measures; plus a [metrics sheet](./recovery-plan/metrics-sheet.csv) and [decision log](./recovery-plan/decision-log-template.md).

## Tests

```bash
python -m unittest discover -s tests -v
```

CI runs exactly this, plus the two demo commands above.

## Layout

```
tool/y2diag/            CLI (y2diag analyze), analyzers/, reports/
tool/config.example.yaml
demo/                   generate_history.py, make_sample_report.py, sample-report/
tracing/                otel-demo/ (services, run_demo.py, compose extras), render_breakdown.py, dashboards/, sample-output/
recovery-plan/          template, metrics sheet, decision log
docs/                   conway-in-practice, common-mistakes, limits
tests/
```

## Known limits

Git mining is a signal, not proof; reports are about **modules and flows, not individuals** (team-level aggregation, never rank people). Static import scanning only. The tracing demo is not the OpenTelemetry SDK. Numbers from the post are *illustrative*; numbers from this repo are *measured on the sample*. See [docs/limits.md](./docs/limits.md).

## License

MIT. See [SECURITY.md](./SECURITY.md) and [CONTRIBUTING.md](./CONTRIBUTING.md).

<sub>[Bence Roth](https://broth.hu/)</sub>
