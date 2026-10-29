# API and jobs contract — revision 1

Semantic envelope fixed; exact OpenAPI shapes/routes are frozen with W02/W03 before UI implementation.

## Operations

Projects/membership; sealed snapshots; scoped fact sets; document versions/anchors; extraction jobs; rule-version reviews; assessments/decisions; comparisons/impact; evidence request responses; review exports; durable job status/events.

Use a versioned API prefix selected in W03 and recorded once. Read models expose explicit states and source baseline. Long operations return 202 with job ID and status URL. Error envelopes include stable code, readable message, field details where appropriate, and request ID. Do not expose internal secrets.

## Mutations

Idempotency key scoped to project, actor, operation, plus request-body hash. Reuse with different body returns conflict. Review uses exact content version and optimistic concurrency. Never mutate sealed assessments or let last-writer-wins overwrite a competing decision.

## Jobs

PostgreSQL owns job/attempt/outbox/event state. Broker schedules at-least-once work. Write job and outbox transactionally; dispatch and reconcile undispatched items/stale leases. Attempt tokens prevent a late worker overwriting a newer attempt. Stage artifacts commit idempotently.

Queued/running/succeeded/failed/cancelled are execution states. Awaiting human review is persisted business state, not a worker held open. Polling first; SSE optional and never authoritative.

Retries are bounded. Cancellation cannot refund completed provider calls. Unknown provider outcomes may cost twice on retry; never promise exactly-once external billing. Redact diagnostic records.

## Integration checks

Unauthorized/cross-project reads and artifacts denied; duplicate request behavior; conflicting reviews; broker duplicate; worker restart before/after stage commit; consistent event ordering; API types matching generated frontend contracts.

