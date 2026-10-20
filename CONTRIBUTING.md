# Contributing

Small, focused changes are welcome.

1. Python 3.10+ and the git CLI. No third-party dependencies - keep it that way.
2. Run the tests: `python -m unittest discover -s tests`
3. If you change analyzers or reports, regenerate the sample and commit it: `python demo/make_sample_report.py` (a test fails if it is stale).
4. Keep outputs deterministic and team-level: never print author names or e-mails.
5. Numbers from the post stay labeled *illustrative*; numbers produced here are labeled *measured on the sample*.
