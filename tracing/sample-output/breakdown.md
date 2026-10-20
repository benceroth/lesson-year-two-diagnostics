# Request-wide breakdown (measured on one local run)

Numbers are wall-clock timings from this run, not benchmarks. 6 concurrent invoice requests share one single-worker export queue in Reporting.

## WITHOUT trace-context propagation

Requests: 6 | median 435 ms | max 646 ms | spans in traces that never join a request: 48

| Request (slowest first) | Total ms | Wait ms (queue/backoff) | Opaque wait ms | Services visible |
|---|---|---|---|---|
| #1 | 646 | 30 | 581 | billing |
| #2 | 556 | 30 | 492 | billing |
| #3 | 475 | 30 | 410 | billing |
| #4 | 395 | 31 | 330 | billing |
| #5 | 315 | 30 | 250 | billing |
| #6 | 234 | 31 | 170 | billing |

### Slowest request (646 ms)

```text
billing: POST /invoices  646 ms
  billing: HTTP GET identity/authorize  31 ms
  billing: invoice.compute  31 ms
  billing: HTTP POST reporting/exports  485 ms
  billing: HTTP POST notifications/notify  11 ms
  billing: notify.retry_backoff  30 ms   <-- WAIT
  billing: HTTP POST notifications/notify  54 ms
```

| Service | Category | ms | % of request | |
|---|---|---|---|---|
| billing | opaque wait (no remote spans) | 581 | 90% | ###################### |
| billing | work | 34 | 5% | # |
| billing | wait (queue/backoff) | 30 | 5% | # |

> 581 ms of this request is spent waiting on services that emitted no spans into this trace. Without shared trace context the cause is invisible.

## WITH W3C traceparent propagation

Requests: 6 | median 432 ms | max 634 ms | spans in traces that never join a request: 0

| Request (slowest first) | Total ms | Wait ms (queue/backoff) | Opaque wait ms | Services visible |
|---|---|---|---|---|
| #1 | 634 | 430 | 0 | billing, identity, notifications, reporting |
| #2 | 554 | 349 | 0 | billing, identity, notifications, reporting |
| #3 | 472 | 269 | 0 | billing, identity, notifications, reporting |
| #4 | 391 | 189 | 0 | billing, identity, notifications, reporting |
| #5 | 312 | 110 | 0 | billing, identity, notifications, reporting |
| #6 | 242 | 30 | 0 | billing, identity, notifications, reporting |

### Slowest request (634 ms)

```text
billing: POST /invoices  634 ms
  billing: HTTP GET identity/authorize  28 ms
    identity: GET /authorize  22 ms
      identity: authz.check  20 ms
  billing: invoice.compute  31 ms
  billing: HTTP POST reporting/exports  485 ms
    reporting: POST /exports  481 ms
      reporting: queue.wait  400 ms   <-- WAIT
      reporting: export.build  80 ms
  billing: HTTP POST notifications/notify  3 ms
    notifications: POST /notify  0 ms
  billing: notify.retry_backoff  30 ms   <-- WAIT
  billing: HTTP POST notifications/notify  54 ms
    notifications: POST /notify  51 ms
      notifications: notify.send  50 ms
```

| Service | Category | ms | % of request | |
|---|---|---|---|---|
| reporting | wait (queue/backoff) | 400 | 63% | ################ |
| reporting | work | 81 | 13% | ### |
| notifications | work | 51 | 8% | ## |
| billing | work | 34 | 5% | # |
| billing | wait (queue/backoff) | 30 | 5% | # |
| identity | work | 22 | 3% | # |
| billing | network + unattributed | 17 | 3% | # |

> 430 ms is queue/backoff wait - time no service would call 'work' and no CPU chart shows.
