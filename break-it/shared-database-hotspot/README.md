# Shared-database hotspot

Three business capabilities import one heavily changed shared database module. The diagnostic should report the database module as a hotspot and show the incoming dependency edges. This is a synthetic code/history signal: the tool cannot inspect a live database or prove runtime contention.

```bash
python break-it/shared-database-hotspot/run.py
```

Expected evidence names `src/shared/database.py` as the highest-churn hotspot and shows Billing, Reporting, and Identity importing `src/shared`.
