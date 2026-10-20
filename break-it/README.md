# Now break it

These offline scenarios create small synthetic Git histories, run the real `y2diag` analyzers, assert the expected finding, and remove their own working repositories. No production data, network, or extra packages are used.

```bash
python break-it/run.py all
```

Or run one case: [hidden coupling](./hidden-coupling/README.md), [team-dependency queue](./team-queue/README.md), or [shared-database hotspot](./shared-database-hotspot/README.md).

The examples demonstrate signals, not proof. In particular, the shared-database case flags change churn and static imports; runtime database contention is outside this tool's scope.
