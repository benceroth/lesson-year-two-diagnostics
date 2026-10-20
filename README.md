# lesson-year-two-diagnostics

[![ci](https://github.com/benceroth/lesson-year-two-diagnostics/actions/workflows/ci.yml/badge.svg)](https://github.com/benceroth/lesson-year-two-diagnostics/actions/workflows/ci.yml)

**The question:** is our year-two pain about infrastructure capacity, or about connections and team structure (Conway's Law)?
**After this you can:** run one command on your own repository and get evidence - change coupling, hotspots, ownership by team, a dependency map - then trace one request to find the wait nobody owns, and start a 90-day recovery plan.

Companion to *Why Scalable Architectures Fail in Year Two—and How to Adapt* (fictional product: HarborLedger). Story link: [read it on Medium](https://medium.com/@benceroth/why-scalable-architectures-fail-in-year-two-6de2be7f6202).

## Run it on your own repo/data

Requires Python 3.10+ and git. No dependencies, no network.

```bash
python y2diag.py analyze /path/to/your/repo --config tool/config.example.yaml --since 2024-01-01
```

The console prints `Analyzed N commits. Findings:` followed by concise signals and the output location. Files go to `y2diag-report/`: `report.md`, `report.html`, `findings.json`, `dependencies.mmd`, `dependencies.dot`. The Markdown/HTML reports contain a summary, co-change pairs, hotspots, team-level ownership and a static dependency map; JSON preserves the structured findings. Start with the summary, then follow a flagged pair or module into its owning team and validate it with a trace.

Copy `tool/config.example.yaml` and adjust the path/team and author/team mappings (CODEOWNERS is honoured when config has no rule). Use `--since`, `--paths`, and `--max-commits` on large repositories. The command reads local git history and sends nothing over the network; review private reports before sharing. Commits are signals, not proof: see [limits](./docs/limits.md).

## Demo first: see output on a synthetic history

```bash
python demo/make_sample_report.py          # builds a reproducible synthetic repo in a temp dir and re-creates demo/sample-report/
```

The committed [sample diagnostic output](./demo/sample-report/diagnostic-output.txt) and [full report](./demo/sample-report/report.md) ([HTML](./demo/sample-report/report.html)) were generated for real from that history. It plants:

| Planted pattern | What the report shows (measured on the sample) |
|---|---|
| `invoice.py` <-> `export.py` change together across teams | 30 co-changes, confidence 1.0 |
| Ownership bottleneck in `src/billing` | edited by 5 teams; the owner authors 35% of changes |
| Hotspot | `invoice.py`: churn 84 x complexity 95.9 |
| Billing <-> Reporting import cycle | mutual dependency in the map |
| A mass reformat touching 40+ files | ignored for coupling (noise) |

Tests assert the analyzers find each of these.

The [before](./demo/sample-report/dependencies-before.svg) and [after](./demo/sample-report/dependencies-after.svg) graphs contrast the measured sample imports with a proposed asynchronous Reporting boundary. They are illustrative design diagrams, not measured post-migration telemetry. Regenerate all artifacts offline with `python demo/make_sample_report.py && python demo/render_dependency_graphs.py`.

## Tracing demo: the hidden queue (no Docker)

```bash
python tracing/otel-demo/run_demo.py
```

Four tiny stdlib HTTP services (Billing, Identity, Reporting, Notifications) propagate W3C `traceparent` and write spans to JSONL. Six concurrent invoice requests share a single-worker export queue in Reporting. The renderer prints a request-wide breakdown twice - see [tracing/sample-output/breakdown.md](./tracing/sample-output/breakdown.md) (measured on one local run, timings vary):

- **Without propagation:** 581 ms of the slowest 646 ms request is one opaque call; nothing says why.
- **With propagation:** the same time resolves to `reporting: queue.wait 400 ms`.

That is the post's "dependencies become queues" claim, made visible. Docker Compose / collector files exist as **unverified** extras ([details](./tracing/otel-demo/README.md)).

## 90-day plan template

Copy [recovery-plan/90-day-template.md](./recovery-plan/90-day-template.md), which uses the post's ranges (Days 1-10, 11-30, 31-45, 46-75, 76-90), evidence checkpoints, and exit measures. Track outcomes in the [metrics sheet](./recovery-plan/metrics-sheet.csv) and decisions in the [decision log](./recovery-plan/decision-log-template.md). The annotated [day-30](https://github.com/benceroth/lesson-year-two-diagnostics/tree/day-30), [day-60](https://github.com/benceroth/lesson-year-two-diagnostics/tree/day-60), and [day-90](https://github.com/benceroth/lesson-year-two-diagnostics/tree/day-90) tags mark the evidence-first progression in this example repository.

## Now break it

Run the [failure-first scenarios](./break-it/README.md) to see the diagnostic flag hidden cross-team coupling, an ownership queue, and a shared-database hotspot. Each case builds a temporary synthetic Git history locally, runs the real analyzers, asserts the signal, and cleans up afterward:

```bash
python break-it/run.py all
```

## Extend it

1. Tune `min_support` and `min_confidence` in a copied config; compare which co-change pairs remain.
2. Add a fourth team to `break-it/team-queue` and verify how the owner-share signal changes.
3. Add a JS/TS relative import to a small fixture and assert the dependency edge in `tests/test_dependency_map.py`.

## Tests

```bash
python -m unittest discover -s tests -v
```

CI runs exactly this, plus the two demo commands above.

## Layout

```
tool/y2diag/            CLI (y2diag analyze), analyzers/, reports/
tool/config.example.yaml
demo/                   synthetic report and graph generators, sample-report/
break-it/               three failure-first scenarios and runners
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
