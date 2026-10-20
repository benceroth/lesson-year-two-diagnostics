# Common mistakes (from the post) and where this repo shows them

| Mistake | What to look at here |
|---|---|
| Equating autoscaling with architecture | `tracing/sample-output/breakdown.md`: more replicas would not shorten a single-worker queue wait or a synchronous chain |
| Splitting services before defining boundaries | coupling and cycle findings persist across a network call; fix boundaries first (`conway-in-practice.md`) |
| Sharing a database across supposedly independent capabilities | the demo's `reporting/read_models.py` imports billing's ledger: an internal-model reach shown as a cross-team edge in the dependency map |
| Measuring traffic but not change friction | `recovery-plan/metrics-sheet.csv`: deployment frequency, lead time, MTTR next to latency |
| Treating observability as a logging project | the "without propagation" run: logs/spans exist but the callee is invisible; with `traceparent` the wait appears |
| Keeping every temporary abstraction forever | `decision-log-template.md`: owner and removal condition for compatibility layers |

Mistakes when *using this tool*:

- Ranking people or teams by commit counts. The report is about modules and flows ([limits.md](./limits.md)).
- Treating a high coupling count as proof. It is a hypothesis to check with the teams and a trace.
- Running it once. Re-run at day 1 and day 90 with the same configuration and compare.
