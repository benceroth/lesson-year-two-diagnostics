# Team-dependency queue

Billing, Identity, and Reporting repeatedly edit one shared module owned by Platform. This should appear as an ownership bottleneck (many teams touch it; the owner authors a minority), not as a ranking of people.

```bash
python break-it/team-queue/run.py
```

Expected evidence includes `src/shared is touched by 4 teams` and an ownership-bottleneck finding.
