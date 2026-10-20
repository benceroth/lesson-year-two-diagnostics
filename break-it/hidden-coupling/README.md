# Hidden coupling

Two capabilities import each other and are changed together across team boundaries. The diagnostic must report the pair as cross-module and cross-team coupling.

```bash
python break-it/hidden-coupling/run.py
```

Expected evidence includes `invoice.py + export.py changed together 9 times` and a strongest cross-module coupling finding.
