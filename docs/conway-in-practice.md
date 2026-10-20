# Conway in practice: reading the reports against team topology

Conway's Law, practically: a technical dependency becomes a scheduling dependency when it crosses a team boundary.
Read each report section as a question about that boundary.

| Signal in the report | Question to ask | Typical response |
|---|---|---|
| Cross-module, cross-team **change coupling** (e.g. `invoice.py` + `export.py`, 30 co-changes) | Why does one change need two teams? | Publish a contract/event; move the shared decision to one owner |
| **Ownership bottleneck**: many teams edit a module, owner authors a minority | Is the owner a queue, or is the module a shared grab-bag? | Split by capability; name maintainers; add contract tests |
| High **inbound share** on a team | Do others wait for this team's context/review? | Reduce the need to edit it (interfaces), not the number of reviewers |
| **Mutual dependency** between modules | Which module is the authority? | Break the cycle with published facts; add direction tests |
| **Hotspot** (churn x complexity) | Is it hard to change *and* changed constantly? | Extract the changing part; add tests; assign an owner |
| Tracing shows a **queue.wait** or opaque client time | Who owns the wait? | Move non-essential work behind a durable queue; give the queue an owner |

## Reading order

1. Dependency map and cycles: where are the connections?
2. Coupling pairs that cross teams: where do connections cost coordination?
3. Ownership: who is waiting on whom?
4. Hotspots: where is the risk concentrated?
5. Trace the flow: where does time go that no one owns?

## Remember

- Clear ownership does not mean one microservice per team. A modular monolith can have named maintainers, contracts and independent tests.
- Many services sharing one database and release calendar are not autonomous.
- Use findings to start a conversation with the teams, then verify with a trace. See [limits.md](./limits.md).
