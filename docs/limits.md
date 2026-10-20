# Limits

Git mining is a **signal, not proof**.

- **Commits are a proxy.** Squash-merges, large commits, bots, and different commit habits distort counts. Commits over `max_files_per_commit` are skipped for coupling and churn; tune it.
- **Coupling is correlation.** Files that change together may share a feature, a template, or a release habit. Confidence is co-changes / commits of the less-changed file; low-history files can look falsely strong (`min_support` guards this).
- **Complexity proxy is crude.** Branch keywords plus lines / 20. It is language-agnostic on purpose, not cyclomatic complexity.
- **Ownership needs a mapping.** Teams come from config path prefixes (win) and CODEOWNERS (simplified matching: last match wins; `*` may cross `/`; only the first `@owner` is used). Authors map to teams by e-mail glob; unmatched authors are `unmapped`. Team reorganizations are not modelled over time.
- **Dependency scanning is static and textual.** It handles Python `import`/`from` and JS/TS relative imports. It misses dynamic imports, aliases (tsconfig paths), packages, service-to-service HTTP calls, and shared databases. Ambiguous Python names are skipped.
- **Working-tree view.** Hotspot complexity and the dependency map read the checked-out files, not the history; check out the revision you want to analyze.
- **Window matters.** Use `--since` to describe the current team shape, not a team that left two years ago.
- **Tracing demo is not OpenTelemetry.** It shows the idea with the W3C traceparent format and sleeps. Real systems need SDKs, sampling, and attention to async hops.
- **Not covered:** runtime coupling, database schema coupling, incident data, DORA metrics collection (the sheet is manual).

## Do not rank people

Reports aggregate by **team** and never print author names or e-mails. Do not use them for performance review or to compare individuals or teams. Teams with fewer than `small_team_authors` (default 3) authors are flagged because counts may identify a person. The input is private history: run locally; nothing is sent over a network.
