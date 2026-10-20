# 90-day recovery plan (template)

Day ranges follow the post: **1-10, 11-30, 31-45, 46-75, 76-90**. Fill in owners and measures for your product.
HarborLedger numbers are the post's *illustrative* scenario, not benchmarks. Track numbers in [metrics-sheet.csv](./metrics-sheet.csv);
record decisions in [decision-log-template.md](./decision-log-template.md).

Pick **one critical flow** (HarborLedger: the invoice request). Do not start by splitting the application.

## Days 1-10: Map the flow

- Trace one request through every capability. Record owners, data reads, synchronous dependencies, retry behavior, failure handling.
- Run `y2diag analyze` on the repository; attach the report.
- Capture baseline: P95 latency, MTTR, deployments per week.
- Find the work the caller does not need to wait for.

| Evidence checkpoint | Owner | Done when |
|---|---|---|
| Flow map with owners and sync dependencies | | reviewed by each capability owner |
| `y2diag` report committed to the decision log | | top coupling/hotspot/bottleneck findings listed |
| Baseline row in metrics sheet | | all columns filled, source of each number noted |

**Exit measure:** baseline recorded; at least one candidate wait or coupling identified with evidence.
(Post: baseline 1.4 s P95, 96 min MTTR, 3 deployments/week; the trace shows completion waits on a Reporting export record.)

## Days 11-30: Establish boundaries and ownership

- Name an owner per capability (business capability, not layer). Add CODEOWNERS and a documented contract each.
- Add tests that stop modules reading each other's internal tables or imports.
- Keep deploying as one unit - reduce uncontrolled dependencies, do not add services.
- Make one capability the authority for its state; others consume published facts.

| Evidence checkpoint | Owner | Done when |
|---|---|---|
| CODEOWNERS covers every module | | `y2diag` shows no `unowned` modules |
| Dependency-direction tests in CI | | a forbidden import fails the build |
| Contract doc per capability | | stable identifiers/events listed |

**Exit measure:** fewer cross-team edges and cycles in the dependency map; owner share of the bottleneck module rising.

## Days 31-45: Instrument the whole request

- Propagate one trace identifier (W3C `traceparent`, OpenTelemetry) through every capability on the flow.
- Dashboards: request P50/P95 latency, error rate; add deployment markers.
- Set targets (post's local goals: P95 <= 350 ms, MTTR <= 30 min - yours will differ).

| Evidence checkpoint | Owner | Done when |
|---|---|---|
| One trace shows all capabilities | | no "opaque" client calls on the critical path |
| Queue/wait visible per hop | | breakdown like `tracing/render_breakdown.py` output |
| Targets written down | | in decision log with a review trigger |

**Exit measure:** a responder can find the slow hop and its owner from one trace id.

## Days 46-75: Extract the measured bottleneck

- Extract only what telemetry justifies. Put it behind a durable queue; publish an event instead of a synchronous call.
- Leave other modules in place unless evidence says otherwise.
- Define timeouts, idempotency, retry limits, backpressure before cut-over.

| Evidence checkpoint | Owner | Done when |
|---|---|---|
| Extraction criteria met and recorded | | distinct scaling/reliability/coordination evidence |
| Queue retry/failure tested | | duplicates, poison messages, backlog covered |
| Rollback path | | reversible without data loss |

**Exit measure:** the non-essential work is off the critical path; latency moves in the expected direction.

## Days 76-90: Review and remove old coupling

- Compare current measures with the baseline.
- Remove the obsolete join/synchronous call and any compatibility layer that has served its purpose.
- Record why the boundary changed and what would reopen the decision.
- Re-run `y2diag`; compare to the day-1 report.

| Evidence checkpoint | Owner | Done when |
|---|---|---|
| Baseline vs. now table | | same definitions as day 1 |
| Old coupling deleted | | `y2diag` no longer lists the pair/cycle |
| Decision log closed with review triggers | | |

**Exit measure:** delivery and recovery signals improved together with the diagram. A cleaner diagram alone is not success.
(Post, illustrative: 330 ms P95, 28 min MTTR, 9 deployments/week.)
